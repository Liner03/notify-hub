import requests

from notify.channels.base import BaseNotifier, REQUIRED
from notify.core.models import ChannelResult


class WeComNotifier(BaseNotifier):
    type_name = "wecom"
    supported_types = {"text", "markdown"}

    @classmethod
    def config(cls) -> dict:
        cfg = super().config()
        cfg.update(
            {
                "webhook": REQUIRED,
                "mentioned_list": None,
                "mentioned_mobile_list": None,
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
        mentions = self.cfg.get("mentioned_list")
        mention_mobiles = self.cfg.get("mentioned_mobile_list")
        content_payload = {"content": content}
        if content_type == "markdown":
            payload = {"msgtype": "markdown", "markdown": content_payload}
        else:
            if mentions:
                content_payload["mentioned_list"] = mentions
            if mention_mobiles:
                content_payload["mentioned_mobile_list"] = mention_mobiles
            payload = {"msgtype": "text", "text": content_payload}

        payload.update(extra)
        try:
            response = requests.post(webhook, json=payload, timeout=timeout)
            return self._result_from_wecom(response)
        except Exception as exc:
            return ChannelResult(False, str(exc))

    def _result_from_wecom(self, response) -> ChannelResult:
        try:
            data = response.json()
        except Exception:
            return self._result_from_response(response)

        if isinstance(data, dict) and "errcode" in data:
            errcode_value = data.get("errcode")
            try:
                errcode = int(errcode_value) if errcode_value is not None else None
            except (TypeError, ValueError):
                errcode = None
            if errcode == 0:
                return ChannelResult(True, "ok")
            message = data.get("errmsg") or f"errcode {errcode_value}"
            return ChannelResult(False, message)

        return self._result_from_response(response)
