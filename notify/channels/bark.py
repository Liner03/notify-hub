from typing import Any
from urllib.parse import quote

import requests

from notify.channels.base import BaseNotifier, REQUIRED
from notify.core.models import ChannelResult

DEFAULT_BARK_SERVER = "https://api.day.app"
EVENT_KEY_FIELD = "event_key"
BARK_QUERY_PARAMS = (
    "level", "volume", "badge", "url", "group", "icon", "sound",
    "call", "autoCopy", "copy", "image", "ciphertext",
    "isArchive", "action", "id", "delete",
)


class BarkNotifier(BaseNotifier):
    type_name = "bark"
    supported_types = {"text", "markdown"}

    @classmethod
    def config(cls) -> dict:
        cfg = super().config()
        cfg.update(
            {
                "key": REQUIRED,
                "server": DEFAULT_BARK_SERVER,
                "title": None,
                "subtitle": None,
                "body": None,
                "level": None,
                "level_map": None,
                "volume": None,
                "badge": None,
                "url": None,
                "group": None,
                "icon": None,
                "sound": None,
                "call": None,
                "autoCopy": None,
                "copy": None,
                "image": None,
                "ciphertext": None,
                "isArchive": None,
                "action": None,
                "id": None,
                "delete": None,
            }
        )
        return cfg

    def send(self, event: dict) -> ChannelResult:
        content_type, content = self._select_content(event)
        key = self.cfg.get("key")
        if not key:
            return ChannelResult(False, "missing key")
        server = self.cfg.get("server") or DEFAULT_BARK_SERVER
        server = server.rstrip("/")
        timeout = self._get_timeout()
        title = self.cfg.get("title")
        subtitle = self.cfg.get("subtitle")
        body = self.cfg.get("body")
        channel_args = self._build_params(event)
        if body is None:
            body = content

        if content_type == "markdown":
            channel_args["markdown"] = content

        # Build path components based on Bark API requirement:
        # - If subtitle exists: /{key}/{title}/{subtitle}/{body}, title defaults to event_key
        # - If only title exists: /{key}/{title}/{body}
        # - Otherwise: /{key}/{body}
        if subtitle:
            if not title:
                title = event.get(EVENT_KEY_FIELD)
            path_parts = [key, title, subtitle, body]
        elif title:
            path_parts = [key, title, body]
        else:
            path_parts = [key, body]

        url = self._build_url(server, path_parts)
        try:
            response = requests.post(
                url,
                params=channel_args or None,
                timeout=timeout,
            )
            return self._result_from_response(response)
        except Exception as exc:
            return ChannelResult(False, str(exc))

    def _build_url(self, server: str, parts: list[str]) -> str:
        encoded_parts = [quote(str(part), safe="") for part in parts]
        return f"{server}/" + "/".join(encoded_parts)

    def _build_params(self, event: dict) -> dict[str, Any]:
        params = {}
        for key in BARK_QUERY_PARAMS:
            value = self.cfg.get(key)
            if value is not None and value is not REQUIRED:
                params[key] = value

        # Handle level mapping from event level to Bark-specific level
        level_map = self.cfg.get("level_map")
        if params.get("level") is None and isinstance(level_map, dict):
            mapped = level_map.get(event.get("level"))
            if mapped:
                params["level"] = mapped
        return params
