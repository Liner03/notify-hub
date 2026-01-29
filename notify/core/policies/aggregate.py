import time
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional

from notify.core.event import build_event
from notify.core.policies.base import BasePolicy, PolicyOutcome
from notify.core.store import MemoryStore


@dataclass
class _AggregateBucket:
    start_time: float
    counts: Dict[str, int] = field(default_factory=dict)
    samples: List[str] = field(default_factory=list)

    def add(self, event: Dict[str, Any], max_samples: int) -> None:
        event_key = event.get("event_key", "")
        self.counts[event_key] = self.counts.get(event_key, 0) + 1
        if len(self.samples) < max_samples:
            raw_content = event.get("raw_content")
            sample_content = str(raw_content) if raw_content else event_key
            self.samples.append(f"{event_key}: {sample_content}")


class AggregatePolicy(BasePolicy):
    def __init__(
        self,
        window: int,
        levels: Optional[Iterable[str]] = None,
        max_samples: int = 5,
    ) -> None:
        self.window = window
        self.levels = {level.lower() for level in (levels or [])}
        self.max_samples = max_samples
        self._buckets: Dict[str, _AggregateBucket] = {}

    def apply(self, event: Dict[str, Any], store: MemoryStore) -> PolicyOutcome:
        meta = event.get("meta") or {}
        if meta.get("aggregate_skip"):
            return PolicyOutcome(action="allow", event=event)

        level = event.get("level", "")
        if self.levels and level not in self.levels:
            return PolicyOutcome(action="allow", event=event)

        bucket_key = self._bucket_key(event)
        bucket = self._buckets.get(bucket_key)
        if bucket is None:
            bucket = _AggregateBucket(start_time=time.time())
            self._buckets[bucket_key] = bucket
        bucket.add(event, self.max_samples)
        return PolicyOutcome(action="suppress", reason="aggregated")

    def flush(self, store: MemoryStore) -> List[Dict[str, Any]]:
        now = time.time()
        results: List[Dict[str, Any]] = []
        for key, bucket in list(self._buckets.items()):
            if now - bucket.start_time < self.window:
                continue
            summary = self._build_summary_event(key, bucket)
            results.append(summary)
            self._buckets.pop(key, None)
        return results

    def _bucket_key(self, event: Dict[str, Any]) -> str:
        source = event.get("source") or "default"
        return f"{event.get('level', '')}:{source}"

    def _build_summary_event(self, bucket_key: str, bucket: _AggregateBucket) -> Dict[str, Any]:
        level, source = bucket_key.split(":", 1)
        lines = [f"window={self.window}s", f"source={source}"]
        for key, count in sorted(bucket.counts.items(), key=lambda x: x[1], reverse=True):
            lines.append(f"- {key}: {count}")
        if bucket.samples:
            lines.append("samples:")
            lines.extend([f"  {sample}" for sample in bucket.samples])
        content = "\n".join(lines)
        return build_event(
            raw_content=content,
            type="text",
            level=level,
            event_key=f"aggregate:{level}:{source}",
            source=source,
            params={},
            meta={"aggregate_skip": True, "aggregate_window": self.window},
        )
