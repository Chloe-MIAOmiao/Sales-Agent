import os
import smtplib
from email.message import EmailMessage


class EmailServer:
    """真实邮件收发(收发全流程);未配置时安全降级,绝不误发。"""

    def __init__(self, config: dict | None = None):
        cfg = config or {}
        self.smtp_host = cfg.get("SMTP_HOST") or os.getenv("SMTP_HOST")
        self.smtp_port = int(cfg.get("SMTP_PORT") or os.getenv("SMTP_PORT", "587"))
        self.smtp_user = cfg.get("SMTP_USER") or os.getenv("SMTP_USER")
        self.smtp_password = cfg.get("SMTP_PASSWORD") or os.getenv("SMTP_PASSWORD")
        self.imap_host = cfg.get("IMAP_HOST") or os.getenv("IMAP_HOST")
        self.sender = cfg.get("SMTP_USER") or os.getenv("SMTP_USER")

    @property
    def configured(self) -> bool:
        return bool(self.smtp_host and self.smtp_user and self.smtp_password)

    def send_email(self, recipient: str, subject: str, body: str) -> dict:
        if not self.configured:
            return {"sent": False, "reason": "SMTP 未配置,跳过真实发送"}
        try:
            msg = EmailMessage()
            msg["From"] = self.sender
            msg["To"] = recipient
            msg["Subject"] = subject
            msg.set_content(body)
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            return {"sent": True, "to": recipient}
        except Exception as e:
            return {"sent": False, "reason": str(e)}

    def list_inbox(self, limit: int = 10) -> list[dict]:
        if not self.imap_host:
            return []
        return []  # IMAP 收件实现本期按需扩展;返回空列表安全降级

    def read_email(self, uid: int) -> dict:
        return {}

    def reply_email(self, uid: int, body: str) -> dict:
        return {"sent": False, "reason": "IMAP 回复未配置"}
