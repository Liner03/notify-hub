import requests

from notify.channels.base import BaseNotifier, REQUIRED
from notify.core.models import ChannelResult


class TelegramNotifier(BaseNotifier):
    type_name = "telegram"
    supported_types = {"text", "markdown", "html"}

    @classmethod
    def config(cls) -> dict:
        cfg = super().config()
        cfg.update(
            {
                "token": REQUIRED,
                "chat_id": REQUIRED,
                "parse_mode": None,
            }
        )
        return cfg

    def send(self, event: dict) -> ChannelResult:
        token = self.cfg.get("token")
        chat_id = self.cfg.get("chat_id")
        if not token or not chat_id:
            return ChannelResult(False, "missing token/chat_id")
        timeout = self.cfg.get("timeout", 10)
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        content_type, content = self._select_content(event)
        payload = {"chat_id": chat_id, "text": content}
        parse_mode = self.cfg.get("parse_mode")
        if not parse_mode:
            if content_type == "markdown":
                parse_mode = "MarkdownV2"
            elif content_type == "html":
                parse_mode = "HTML"
        if parse_mode:
            payload["parse_mode"] = parse_mode

        payload.update(self._extra_config({"token", "chat_id", "timeout", "parse_mode"}))
        try:
            response = requests.post(url, json=payload, timeout=timeout)
            return self._result_from_response(response)
        except Exception as exc:
            return ChannelResult(False, str(exc))
