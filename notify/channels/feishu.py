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
        timeout = self._get_timeout()
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
            return self._result_from_feishu(response)
        except Exception as exc:
            return ChannelResult(False, str(exc))

    def _result_from_feishu(self, response) -> ChannelResult:
        try:
            data = response.json()
        except Exception:
            return self._result_from_response(response)

        if isinstance(data, dict):
            if "code" in data:
                code_value = data.get("code")
            elif "StatusCode" in data:
                code_value = data.get("StatusCode")
            elif "errcode" in data:
                code_value = data.get("errcode")
            else:
                code_value = None

            if code_value is not None:
                try:
                    code_int = int(code_value)
                except (TypeError, ValueError):
                    code_int = None
                if code_int == 0:
                    return ChannelResult(True, "ok")
                message = (
                    data.get("msg")
                    or data.get("message")
                    or data.get("errmsg")
                    or data.get("StatusMessage")
                    or f"code {code_value}"
                )
                return ChannelResult(False, message)

        return self._result_from_response(response)
