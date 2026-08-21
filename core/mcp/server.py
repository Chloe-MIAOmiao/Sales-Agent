import os
from pathlib import Path

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from core.mcp.email_server import EmailServer

_ENV_KEYS = ("SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD", "IMAP_HOST")


def load_env_config() -> dict:
    load_dotenv(Path.cwd() / ".env")
    return {k: os.environ[k] for k in _ENV_KEYS if k in os.environ}


def build_email_mcp_server(config: dict | None = None) -> FastMCP:
    email = EmailServer(config if config is not None else load_env_config())
    server: FastMCP = FastMCP("sales-agent-email")

    @server.tool()
    def send_email(recipient: str, subject: str, body: str) -> dict:
        """发送合规跟进邮件(需人工批准后调用);未配置 SMTP 时安全降级。"""
        return email.send_email(recipient, subject, body)

    return server


if __name__ == "__main__":
    build_email_mcp_server().run()
