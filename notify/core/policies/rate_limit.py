import time
from typing import Any, Dict, Iterable, Optional
from notify.core.policies.base import BasePolicy, PolicyOutcome
from notify.core.store import MemoryStore


class RateLimitPolicy(BasePolicy):
    def __init__(
        self,
        per_minute: int,
        levels: Optional[Iterable[str]] = None,
        scope: str = "global",
    ) -> None:
        self.per_minute = per_minute
        self.levels = {level.lower() for level in (levels or [])}
        self.scope = scope

    def apply(self, event: Dict[str, Any], store: MemoryStore) -> PolicyOutcome:
        level = event.get("level", "")
        if self.levels and level not in self.levels:
            return PolicyOutcome(action="allow", event=event)

        minute_bucket = int(time.time() // 60)
        if self.scope == "event_key":
            key = f"rate:{event.get('event_key', '')}:{minute_bucket}"
        elif self.scope == "level":
            key = f"rate:{level}:{minute_bucket}"
        else:
            key = f"rate:global:{minute_bucket}"

        count = store.increment(key, ttl=120)
        if count > self.per_minute:
            return PolicyOutcome(action="suppress", reason="rate_limited")

        return PolicyOutcome(action="allow", event=event)
