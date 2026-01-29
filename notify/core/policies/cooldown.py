from typing import Any, Dict, Iterable, Optional
from notify.core.policies.base import BasePolicy, PolicyOutcome
from notify.core.store import MemoryStore


class CooldownPolicy(BasePolicy):
    def __init__(self, ttl: int, levels: Optional[Iterable[str]] = None) -> None:
        self.ttl = ttl
        self.levels = {level.lower() for level in (levels or [])}

    def apply(self, event: Dict[str, Any], store: MemoryStore) -> PolicyOutcome:
        level = event.get("level", "")
        if self.levels and level not in self.levels:
            return PolicyOutcome(action="allow", event=event)

        key = f"cooldown:{event.get('event_key', '')}"
        if store.is_active(key):
            return PolicyOutcome(action="suppress", reason="cooldown")

        store.set_expiry(key, self.ttl)
        return PolicyOutcome(action="allow", event=event)
