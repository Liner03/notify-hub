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
        timeout = self.cfg.get("timeout", 10)
        content_type, content = self._select_content(event)
        extra = self.cfg.get("extra")
        if not isinstance(extra, dict):
            extra = {}
        mentions = self.cfg.get("mentioned_list")
        mention_mobiles = self.cfg.get("mentioned_mobile_list")
        content_payload = {"content": content}
        if mentions:
            content_payload["mentioned_list"] = mentions
        if mention_mobiles:
            content_payload["mentioned_mobile_list"] = mention_mobiles
        if content_type == "markdown":
            payload = {"msgtype": "markdown", "markdown": content_payload}
        else:
            payload = {"msgtype": "text", "text": content_payload}

        payload.update(extra)
        try:
            response = requests.post(webhook, json=payload, timeout=timeout)
            return self._result_from_response(response)
        except Exception as exc:
            return ChannelResult(False, str(exc))
