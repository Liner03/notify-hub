from typing import Any, Dict, Iterable, Optional
from notify.core.policies.base import BasePolicy, PolicyOutcome
from notify.core.store import MemoryStore


class DedupePolicy(BasePolicy):
    def __init__(
        self,
        ttl: int,
        levels: Optional[Iterable[str]] = None,
        upgrade_after: Optional[int] = None,
    ) -> None:
        self.ttl = ttl
        self.levels = {level.lower() for level in (levels or [])}
        self.upgrade_after = upgrade_after

    def apply(self, event: Dict[str, Any], store: MemoryStore) -> PolicyOutcome:
        level = event.get("level", "")
        if self.levels and level not in self.levels:
            return PolicyOutcome(action="allow", event=event)

        event_key = event.get("event_key", "")
        key = f"dedupe:{event_key}"
        suppress_key = f"suppress:{event_key}"

        if store.is_active(key):
            suppressed_count = store.increment(suppress_key, ttl=self.ttl)
            if self.upgrade_after and suppressed_count >= self.upgrade_after:
                store.reset(suppress_key)
                store.set_expiry(key, self.ttl)
                return PolicyOutcome(action="allow", event=event)

            return PolicyOutcome(action="suppress", reason="deduped")

        store.set_expiry(key, self.ttl)
        store.reset(suppress_key)
        return PolicyOutcome(action="allow", event=event)
