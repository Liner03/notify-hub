from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from notify.core.store import MemoryStore


@dataclass
class PolicyOutcome:
    action: str
    reason: Optional[str] = None
    event: Optional[Dict[str, Any]] = None


class BasePolicy:
    def apply(self, event: Dict[str, Any], store: MemoryStore) -> PolicyOutcome:
        return PolicyOutcome(action="allow", event=event)

    def flush(self, store: MemoryStore) -> List[Dict[str, Any]]:
        return []
