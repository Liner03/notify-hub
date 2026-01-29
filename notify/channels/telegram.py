import requests

from notify.channels.base import BaseNotifier
from notify.core.models import ChannelResult


class TelegramNotifier(BaseNotifier):
    type_name = "telegram"
    supported_types = {"text", "markdown", "html"}

    def __init__(self, token: str, chat_id: str, name=None, timeout: int = 10) -> None:
        super().__init__(name=name)
        self.token = token
        self.chat_id = chat_id
        self.timeout = timeout

    def send(self, event: dict) -> ChannelResult:
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        content_type, content = self._select_content(event)
        payload = {"chat_id": self.chat_id, "text": content}
        if content_type == "markdown":
            payload["parse_mode"] = "MarkdownV2"
        elif content_type == "html":
            payload["parse_mode"] = "HTML"

        payload.update(self._channel_args(event))
        try:
            response = requests.post(url, json=payload, timeout=self.timeout)
            if response.status_code >= 400:
                return ChannelResult(False, f"http {response.status_code}")
            return ChannelResult(True)
        except Exception as exc:
            return ChannelResult(False, str(exc))
