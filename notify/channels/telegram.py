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
        timeout = self._get_timeout()
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

        payload.update(self._extra_config({"token", "chat_id", "timeout", "parse_mode", "text"}))
        try:
            response = requests.post(url, json=payload, timeout=timeout)
            return self._result_from_telegram(response)
        except requests.exceptions.Timeout:
            return ChannelResult(False, "send timeout")
        except requests.exceptions.ConnectionError:
            return ChannelResult(False, "send connection failed")
        except Exception as exc:
            return ChannelResult(False, f"send failed: {type(exc).__name__}")

    def _result_from_telegram(self, response) -> ChannelResult:
        try:
            data = response.json()
        except Exception:
            return self._result_from_response(response)

        if isinstance(data, dict):
            ok = data.get("ok")
            if ok is True:
                return ChannelResult(True, "ok")
            if ok is False:
                message = data.get("description")
                if not message and "error_code" in data:
                    message = f"error_code {data.get('error_code')}"
                return ChannelResult(False, message or "telegram error")

        return self._result_from_response(response)
