from urllib.parse import quote

import requests

from notify.channels.base import BaseNotifier
from notify.core.models import ChannelResult


class BarkNotifier(BaseNotifier):
    type_name = "bark"
    supported_types = {"text"}

    def __init__(
        self,
        key: str,
        server: str = "https://api.day.app",
        name=None,
        timeout: int = 10,
    ) -> None:
        super().__init__(name=name)
        self.key = key
        self.server = (server or "https://api.day.app").rstrip("/")
        self.timeout = timeout

    def send(self, event: dict) -> ChannelResult:
        _, content = self._select_content(event)
        channel_args = self._channel_args(event)
        title = channel_args.pop("title", None)
        subtitle = channel_args.pop("subtitle", None)
        body = channel_args.pop("body", None)
        if body is None:
            body = content

        if subtitle:
            if not title:
                title = event.get("event_key")
            path_parts = [self.key, title, subtitle, body]
        elif title:
            path_parts = [self.key, title, body]
        else:
            path_parts = [self.key, body]

        url = self._build_url(path_parts)
        try:
            response = requests.post(
                url,
                params=channel_args or None,
                timeout=self.timeout,
            )
            if response.status_code >= 400:
                return ChannelResult(False, f"http {response.status_code}")
            return ChannelResult(True)
        except Exception as exc:
            return ChannelResult(False, str(exc))

    def _build_url(self, parts) -> str:
        encoded_parts = [quote(str(part), safe="") for part in parts]
        return f"{self.server}/" + "/".join(encoded_parts)

    def _inline_params(self, event: dict) -> dict:
        params = event.get("params") or {}
        if not isinstance(params, dict):
            return {}
        allowlist = {
            "title",
            "subtitle",
            "body",
            "markdown",
            "device_key",
            "device_keys",
            "level",
            "volume",
            "badge",
            "url",
            "group",
            "icon",
            "sound",
            "call",
            "autoCopy",
            "copy",
            "image",
            "ciphertext",
            "isArchive",
            "action",
            "id",
            "delete",
        }
        return {key: params[key] for key in allowlist if key in params}
