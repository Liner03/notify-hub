import requests

from notify.channels.base import BaseNotifier
from notify.core.models import ChannelResult


class WeComNotifier(BaseNotifier):
    type_name = "wecom"
    supported_types = {"text", "markdown"}

    def __init__(self, webhook: str, name=None, timeout: int = 10) -> None:
        super().__init__(name=name)
        self.webhook = webhook
        self.timeout = timeout

    def send(self, event: dict) -> ChannelResult:
        content_type, content = self._select_content(event)
        if content_type == "markdown":
            payload = {"msgtype": "markdown", "markdown": {"content": content}}
        else:
            payload = {"msgtype": "text", "text": {"content": content}}

        payload.update(self._channel_args(event))
        try:
            response = requests.post(self.webhook, json=payload, timeout=self.timeout)
            if response.status_code >= 400:
                return ChannelResult(False, f"http {response.status_code}")
            return ChannelResult(True)
        except Exception as exc:
            return ChannelResult(False, str(exc))
