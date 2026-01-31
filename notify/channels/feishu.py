import requests

from notify.channels.base import BaseNotifier, REQUIRED
from notify.core.models import ChannelResult


class FeishuNotifier(BaseNotifier):
    type_name = "feishu"
    supported_types = {"text", "markdown"}

    @classmethod
    def config(cls) -> dict:
        cfg = super().config()
        cfg.update(
            {
                "webhook": REQUIRED,
                "extra": {},
            }
        )
        return cfg

    def send(self, event: dict) -> ChannelResult:
        webhook = self.cfg.get("webhook")
        if not webhook:
            return ChannelResult(False, "missing webhook")
        timeout = self.cfg.get("timeout", 10)
        content_type, content = self._select_content(event)
        extra = self.cfg.get("extra")
        if not isinstance(extra, dict):
            extra = {}
        if content_type == "markdown":
            payload = {
                "msg_type": "interactive",
                "card": {
                    "config": {"wide_screen_mode": True},
                    "elements": [
                        {"tag": "markdown", "content": content}
                    ],
                },
            }
        else:
            payload = {
                "msg_type": "text",
                "content": {"text": content},
            }

        payload.update(extra)
        try:
            response = requests.post(webhook, json=payload, timeout=timeout)
            if response.status_code >= 400:
                return ChannelResult(False, f"http {response.status_code}")
            return ChannelResult(True)
        except Exception as exc:
            return ChannelResult(False, str(exc))
