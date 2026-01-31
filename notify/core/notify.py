from typing import Any, Dict, Iterable, List, Optional

from notify.channels import BarkNotifier, FeishuNotifier, TelegramNotifier, WeComNotifier
from notify.core.config import load_config
from notify.core.event import build_event
from notify.core.models import DispatchResult, SendResult
from notify.core.policies.aggregate import AggregatePolicy
from notify.core.policies.cooldown import CooldownPolicy
from notify.core.policies.dedupe import DedupePolicy
from notify.core.policies.rate_limit import RateLimitPolicy
from notify.core.registry import NotifierRegistry
from notify.core.store import MemoryStore


class Notify:
    def __init__(
        self,
        channels: Iterable,
        policies: Iterable = (),
        store: Optional[MemoryStore] = None,
    ) -> None:
        self.channels = list(channels)
        self.policies = list(policies)
        self.store = store or MemoryStore()

    @classmethod
    def from_config(cls, path: Optional[str] = None) -> "Notify":
        _register_builtin_channels()
        config = load_config(path or "notify.yaml")
        channels = _build_channels(config.get("channels", []))
        policies = _build_policies(config.get("policies", {}))
        return cls(channels=channels, policies=policies)

    def send(
        self,
        raw_content: Any,
        type: str = "text",
        notify_level: str = "info",
        event_key: Optional[str] = None,
        source: Optional[str] = None,
    ) -> SendResult:
        event = build_event(
            raw_content=raw_content,
            type=type,
            level=notify_level,
            event_key=event_key,
            source=source,
        )

        results: List[DispatchResult] = []

        for policy in self.policies:
            flush_events = policy.flush(self.store)
            for flush_event in flush_events:
                results.append(self._dispatch(flush_event))

        outcome_event = event
        for policy in self.policies:
            outcome = policy.apply(outcome_event, self.store)
            if outcome.action == "suppress":
                results.append(
                    DispatchResult(
                        event_key=outcome_event.get("event_key", ""),
                        status="suppressed",
                        channel_results={},
                        reason=outcome.reason,
                    )
                )
                return SendResult(status="suppressed", results=results)
            outcome_event = outcome.event or outcome_event

        results.append(self._dispatch(outcome_event))
        status = "sent"
        if any(r.status == "failed" for r in results):
            status = "failed"
        elif any(r.status == "partial" for r in results):
            status = "partial"
        return SendResult(status=status, results=results)

    def _dispatch(self, event: Dict[str, Any]) -> DispatchResult:
        channel_results = {}
        success_count = 0
        for channel in self.channels:
            result = channel.send(event)
            channel_results[channel.name] = result
            if result.success:
                success_count += 1

        if success_count == len(self.channels):
            status = "sent"
        elif success_count == 0:
            status = "failed"
        else:
            status = "partial"

        return DispatchResult(
            event_key=event.get("event_key", ""),
            status=status,
            channel_results=channel_results,
        )


def _register_builtin_channels() -> None:
    NotifierRegistry.register("telegram", TelegramNotifier)
    NotifierRegistry.register("wecom", WeComNotifier)
    NotifierRegistry.register("feishu", FeishuNotifier)
    NotifierRegistry.register("bark", BarkNotifier)


def _build_channels(channel_configs: List[Dict[str, Any]]):
    channels = []
    for item in channel_configs:
        channel_type = item.get("type")
        if not channel_type:
            raise ValueError("channel missing type")
        params = {k: v for k, v in item.items() if k != "type"}
        config_overrides = params.pop("config", None)
        if isinstance(config_overrides, dict):
            params.update(config_overrides)
        channels.append(NotifierRegistry.create(channel_type, **params))
    if not channels:
        raise ValueError("no channels configured")
    return channels


def _build_policies(policy_configs: Dict[str, Any]):
    policies = []
    dedupe_cfg = policy_configs.get("dedupe")
    if dedupe_cfg:
        policies.append(
            DedupePolicy(
                ttl=int(dedupe_cfg.get("ttl", 3600)),
                levels=dedupe_cfg.get("levels") or [],
                upgrade_after=dedupe_cfg.get("upgrade_after"),
            )
        )

    cooldown_cfg = policy_configs.get("cooldown")
    if cooldown_cfg:
        policies.append(
            CooldownPolicy(
                ttl=int(cooldown_cfg.get("ttl", 3600)),
                levels=cooldown_cfg.get("levels") or [],
            )
        )

    rate_cfg = policy_configs.get("rate_limit")
    if rate_cfg:
        policies.append(
            RateLimitPolicy(
                per_minute=int(rate_cfg.get("per_minute", 30)),
                levels=rate_cfg.get("levels") or [],
                scope=rate_cfg.get("scope", "global"),
            )
        )

    agg_cfg = policy_configs.get("aggregate")
    if agg_cfg:
        policies.append(
            AggregatePolicy(
                window=int(agg_cfg.get("window", 3600)),
                levels=agg_cfg.get("levels") or ["warn"],
                max_samples=int(agg_cfg.get("max_samples", 5)),
            )
        )

    return policies
