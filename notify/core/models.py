from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class ChannelResult:
    success: bool
    message: Optional[str] = None


@dataclass
class DispatchResult:
    event_key: str
    status: str
    channel_results: Dict[str, ChannelResult]
    reason: Optional[str] = None


@dataclass
class SendResult:
    status: str
    results: List[DispatchResult]
