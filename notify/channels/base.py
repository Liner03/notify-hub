from copy import deepcopy
from typing import Any, Dict, Optional, Tuple

from notify.core.models import ChannelResult


REQUIRED = object()


class BaseNotifier:
    type_name = "base"
    supported_types = {"text"}

    def __init__(self, name: Optional[str] = None, **overrides) -> None:
        self.name = name or self.type_name
        defaults = self.config()
        if not isinstance(defaults, dict):
            raise TypeError("config() must return a dict")
        self.cfg = self._merge_config(defaults, overrides)
        self._validate_config(defaults)

    @classmethod
    def config(cls) -> Dict[str, Any]:
        return {"timeout": 10}

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

    def _merge_config(self, defaults: Dict[str, Any], overrides: Dict[str, Any]) -> Dict[str, Any]:
        merged = deepcopy(defaults)
        for key, value in overrides.items():
            merged[key] = value
        return merged

    def _validate_config(self, defaults: Dict[str, Any]) -> None:
        missing = []
        for key, value in defaults.items():
            if value is REQUIRED:
                if self.cfg.get(key) in (None, REQUIRED):
                    missing.append(key)
        if missing:
            raise ValueError(f"{self.name} missing config: {', '.join(missing)}")

    def _result_from_response(self, response) -> ChannelResult:
        status = getattr(response, "status_code", None)
        text = getattr(response, "text", "")
        message = (text or "").strip()
        if status is None:
            return ChannelResult(False, "missing status_code")
        if status >= 400:
            return ChannelResult(False, message or f"http {status}")
        return ChannelResult(True, message or "ok")

    def _extra_config(self, exclude: set) -> Dict[str, Any]:
        extras: Dict[str, Any] = {}
        for key, value in self.cfg.items():
            if key in exclude:
                continue
            if value is REQUIRED or value is None:
                continue
            extras[key] = value
        return extras
