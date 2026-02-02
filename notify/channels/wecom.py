import json
import re
import time

import requests

from notify.channels.base import BaseNotifier, REQUIRED
from notify.core.models import ChannelResult


TOKEN_URL = "https://qyapi.weixin.qq.com/cgi-bin/gettoken"
SEND_URL = "https://qyapi.weixin.qq.com/cgi-bin/message/send"
ACCESS_TOKEN_RE = re.compile(r"(access_token=)([^&]*)")


class WeComNotifier(BaseNotifier):
    type_name = "wecom"
    supported_types = {
        "text",
        "markdown",
        "markdown_v2",
        "image",
        "news",
        "file",
        "voice",
        "mpnews",
        "video",
        "textcard",
        "template_card",
    }

    def __init__(self, name: str | None = None, **overrides) -> None:
        super().__init__(name=name, **overrides)
        self._access_token = None
        self._token_expiry = 0.0

    @classmethod
    def config(cls) -> dict:
        cfg = super().config()
        cfg.update(
            {
                "corpid": REQUIRED,
                "corpsecret": REQUIRED,
                "agentid": REQUIRED,
                "touser": None,
                "toparty": None,
                "totag": None,
                "msgtype": None,
                "payload": None,
                "base_url": TOKEN_URL,
                "req_url": SEND_URL,
                "safe": 0,
                "enable_id_trans": 0,
                "enable_duplicate_check": 0,
                "duplicate_check_interval": 1800,
                "extra": {},
            }
        )
        return cfg

    def send(self, event: dict) -> ChannelResult:
        corpid = self.cfg.get("corpid")
        corpsecret = self.cfg.get("corpsecret")
        agentid = self.cfg.get("agentid")
        if not corpid or not corpsecret:
            return ChannelResult(False, "missing corpid/corpsecret")
        if agentid in (None, REQUIRED):
            return ChannelResult(False, "missing agentid")

        timeout = self._get_timeout()
        token = self._get_access_token(corpid, corpsecret, timeout)
        if isinstance(token, ChannelResult):
            return token

        content_type, content = self._select_content(event)
        msgtype = self.cfg.get("msgtype") or content_type
        if not isinstance(msgtype, str):
            return ChannelResult(False, "invalid msgtype")
        msgtype = msgtype.strip().lower()
        if not msgtype:
            return ChannelResult(False, "missing msgtype")

        payload_override = self.cfg.get("payload")
        if payload_override is not None and not isinstance(payload_override, dict):
            return ChannelResult(False, "payload must be a dict")

        body = payload_override
        if body is None:
            body = self._build_message_body(msgtype, content)
            if isinstance(body, ChannelResult):
                return body

        message = self._build_message_envelope(msgtype, body, agentid)
        if isinstance(message, ChannelResult):
            return message

        extra = self.cfg.get("extra")
        if isinstance(extra, dict):
            for key, value in extra.items():
                if key in {"msgtype", msgtype}:
                    continue
                message[key] = value

        send_url = self._build_send_url(token)
        try:
            response = requests.post(send_url, json=message, timeout=timeout)
            return self._result_from_wecom(response)
        except requests.exceptions.Timeout:
            return ChannelResult(False, "send timeout")
        except requests.exceptions.ConnectionError:
            return ChannelResult(False, "send connection failed")
        except Exception as exc:
            return ChannelResult(False, f"send failed: {type(exc).__name__}")

    def _build_message_body(self, msgtype: str, content: str):
        if msgtype in {"text", "markdown", "markdown_v2"}:
            return {"content": content}
        return self._parse_structured_payload(msgtype, content)

    def _build_message_envelope(self, msgtype: str, body: dict, agentid) -> dict | ChannelResult:
        try:
            agentid_int = int(agentid)
        except (TypeError, ValueError):
            return ChannelResult(False, "invalid agentid")

        message = {
            "msgtype": msgtype,
            "agentid": agentid_int,
            msgtype: body,
        }

        touser = self._normalize_target(self.cfg.get("touser"))
        toparty = self._normalize_target(self.cfg.get("toparty"))
        totag = self._normalize_target(self.cfg.get("totag"))

        if not (touser or toparty or totag):
            return ChannelResult(False, "missing touser/toparty/totag")

        if touser:
            message["touser"] = touser
        if toparty:
            message["toparty"] = toparty
        if totag:
            message["totag"] = totag

        for key in (
            "safe",
            "enable_id_trans",
            "enable_duplicate_check",
            "duplicate_check_interval",
        ):
            value = self.cfg.get(key)
            if value is not None and value is not REQUIRED:
                message[key] = value

        return message

    def _normalize_target(self, value):
        if value is None or value is REQUIRED:
            return None
        if isinstance(value, (list, tuple, set)):
            items = [str(item) for item in value if item]
            if not items:
                return None
            return "|".join(items)
        text = str(value).strip()
        return text or None

    def _build_send_url(self, token: str) -> str:
        req_url = self.cfg.get("req_url") or SEND_URL
        if not isinstance(req_url, str):
            req_url = SEND_URL
        req_url = req_url.strip()
        if "access_token=" in req_url:
            if req_url.endswith("access_token="):
                return req_url + token
            return ACCESS_TOKEN_RE.sub(r"\1" + token, req_url)
        sep = "&" if "?" in req_url else "?"
        return req_url.rstrip("?") + f"{sep}access_token=" + token

    def _get_access_token(self, corpid: str, corpsecret: str, timeout):
        now = time.time()
        if self._access_token and now < self._token_expiry:
            return self._access_token

        token_url = self.cfg.get("base_url") or TOKEN_URL
        if not isinstance(token_url, str):
            token_url = TOKEN_URL
        token_url = token_url.strip().rstrip("?")
        try:
            response = requests.get(
                token_url,
                params={"corpid": corpid, "corpsecret": corpsecret},
                timeout=timeout,
            )
        except requests.exceptions.Timeout:
            return ChannelResult(False, "get token timeout")
        except requests.exceptions.ConnectionError:
            return ChannelResult(False, "get token connection failed")
        except Exception as exc:
            return ChannelResult(False, f"get token failed: {type(exc).__name__}")

        if response.status_code >= 400:
            return self._result_from_response(response)

        try:
            data = response.json()
        except Exception:
            return ChannelResult(False, "invalid token response")

        errcode_value = data.get("errcode")
        try:
            errcode = int(errcode_value) if errcode_value is not None else None
        except (TypeError, ValueError):
            errcode = None
        if errcode != 0:
            message = data.get("errmsg") or f"errcode {errcode_value}"
            return ChannelResult(False, message)

        token = data.get("access_token")
        if not token:
            return ChannelResult(False, "missing access_token")
        expires_in = data.get("expires_in", 7200)
        try:
            expires_in = int(expires_in)
        except (TypeError, ValueError):
            expires_in = 7200
        self._access_token = token
        self._token_expiry = now + max(expires_in - 60, 0)
        return token

    def _parse_structured_payload(self, msgtype: str, content: str):
        raw = (content or "").strip()
        if not raw:
            return ChannelResult(False, f"missing {msgtype} payload")
        if msgtype in {"image", "file", "voice"}:
            if raw.startswith("{"):
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError:
                    return ChannelResult(False, f"invalid json for {msgtype}")
                if not isinstance(data, dict):
                    return ChannelResult(False, f"invalid {msgtype} payload")
                return data
            return {"media_id": raw}
        if msgtype in {"news", "mpnews"}:
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                return ChannelResult(False, f"invalid json for {msgtype}")
            if isinstance(data, dict) and "articles" in data:
                return data
            if isinstance(data, list):
                return {"articles": data}
            return ChannelResult(False, f"invalid {msgtype} payload")
        if msgtype in {"template_card", "textcard"}:
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                return ChannelResult(False, f"invalid json for {msgtype}")
            if not isinstance(data, dict):
                return ChannelResult(False, f"invalid {msgtype} payload")
            return data

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return ChannelResult(False, f"invalid json for {msgtype}")
        if not isinstance(data, dict):
            return ChannelResult(False, f"invalid {msgtype} payload")
        return data

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
