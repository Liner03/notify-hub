import requests

from notify.channels.base import BaseNotifier
from notify.core.models import ChannelResult


class WebhookBaseNotifier(BaseNotifier):
    type_name = "webhook"
    supported_types = {"text", "markdown", "html", "json"}

    def __init__(self, url: str, name=None, timeout: int = 10, headers=None) -> None:
        super().__init__(name=name)
        self.url = url
        self.timeout = timeout
        self.headers = headers or {}

    def send(self, event: dict) -> ChannelResult:
        channel_args = self._channel_args(event)
        payload = self.build_payload(event, channel_args)
        headers = self.build_headers(event, channel_args)

        try:
            response = requests.post(
                self.url,
                json=payload,
                headers=headers,
                timeout=self.timeout,
            )
            if response.status_code >= 400:
                return ChannelResult(False, f"http {response.status_code}")
            return ChannelResult(True)
        except Exception as exc:
            return ChannelResult(False, str(exc))

    def build_payload(self, event: dict, channel_args: dict) -> dict:
        return {
            "event_key": event.get("event_key"),
            "level": event.get("level"),
            "raw_content": event.get("raw_content"),
            "type": event.get("type"),
            "source": event.get("source"),
            "context": event.get("context") or {},
            "timestamp": event.get("timestamp"),
            "meta": event.get("meta") or {},
            "channel": self.name,
            "params": channel_args,
        }

    def build_headers(self, event: dict, channel_args: dict) -> dict:
        return {"X-Event-Key": event.get("event_key", ""), **self.headers}
