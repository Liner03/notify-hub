from typing import Any, Dict, Optional, Tuple

from notify.core.models import ChannelResult


class BaseNotifier:
    type_name = "base"
    supported_types = {"text"}

    def __init__(self, name: Optional[str] = None) -> None:
        self.name = name or self.type_name

    def send(self, event: Dict[str, Any]) -> ChannelResult:
        raise NotImplementedError

    def _select_content(self, event: Dict[str, Any]) -> Tuple[str, str]:
        content_type = (event.get("type") or "text").lower()
        if content_type not in self.supported_types:
            content_type = "text"
        content = event.get("raw_content")
        if content is None:
            content = ""
        return content_type, str(content)

    def _channel_args(self, event: Dict[str, Any]) -> Dict[str, Any]:
        params = event.get("params") or {}
        if not isinstance(params, dict):
            return {}

        merged: Dict[str, Any] = {}
        merged.update(self._prefixed_params(params, "common_"))
        merged.update(self._inline_params(event))
        merged.update(self._prefixed_params(params, f"{self.type_name}_"))
        if self.name != self.type_name:
            merged.update(self._prefixed_params(params, f"{self.name}_"))
        return merged

    def _prefixed_params(self, params: Dict[str, Any], prefix: str) -> Dict[str, Any]:
        selected: Dict[str, Any] = {}
        if not prefix:
            return selected
        for key, value in params.items():
            if not isinstance(key, str):
                continue
            if key.startswith(prefix):
                stripped = key[len(prefix):]
                if stripped:
                    selected[stripped] = value
        return selected

    def _inline_params(self, event: Dict[str, Any]) -> Dict[str, Any]:
        return {}
