import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Any, Dict

from notify.channels.base import BaseNotifier, REQUIRED
from notify.core.models import ChannelResult


class EmailNotifier(BaseNotifier):
    type_name = "email"
    supported_types = {"text", "html"}

    @classmethod
    def config(cls) -> Dict[str, Any]:
        cfg = super().config()
        cfg.update(
            {
                "host": REQUIRED,
                "port": 465,
                "username": REQUIRED,
                "password": REQUIRED,
                "from_addr": None,
                "to_addrs": REQUIRED,
                "subject": None,
                "use_ssl": True,
                "timeout": 10,
            }
        )
        return cfg

    def send(self, event: Dict[str, Any]) -> ChannelResult:
        content_type, content = self._select_content(event)

        # 获取配置
        host = self.cfg.get("host")
        port = self.cfg.get("port", 465)
        username = self.cfg.get("username")
        password = self.cfg.get("password")
        from_addr = self.cfg.get("from_addr") or username
        to_addrs = self.cfg.get("to_addrs")
        subject = self.cfg.get("subject") or event.get("event_key", "Notification")
        use_ssl = self.cfg.get("use_ssl", True)
        timeout = self._get_timeout()

        # 处理收件人地址 (支持字符串或列表)
        if isinstance(to_addrs, str):
            to_addrs = [to_addrs]
        elif not isinstance(to_addrs, list):
            return ChannelResult(False, "to_addrs must be string or list")

        # 构建邮件
        msg = MIMEMultipart("alternative")
        msg["From"] = from_addr
        msg["To"] = ", ".join(to_addrs)
        msg["Subject"] = subject

        # 根据内容类型添加内容
        if content_type == "html":
            msg.attach(MIMEText(content, "html", "utf-8"))
        else:
            msg.attach(MIMEText(content, "plain", "utf-8"))

        # 发送邮件
        try:
            if use_ssl:
                # 使用 SSL (端口 465)
                with smtplib.SMTP_SSL(host, port, timeout=timeout) as server:
                    server.login(username, password)
                    server.send_message(msg)
            else:
                # 使用 STARTTLS (端口 587)
                with smtplib.SMTP(host, port, timeout=timeout) as server:
                    server.starttls()
                    server.login(username, password)
                    server.send_message(msg)

            return ChannelResult(True, "email sent successfully")
        except smtplib.SMTPAuthenticationError as exc:
            return ChannelResult(False, f"authentication failed: {type(exc).__name__}")
        except smtplib.SMTPException as exc:
            return ChannelResult(False, f"smtp error: {type(exc).__name__}")
        except Exception as exc:
            return ChannelResult(False, f"connection error: {type(exc).__name__}")
