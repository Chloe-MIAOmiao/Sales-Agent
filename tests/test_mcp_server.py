import asyncio
import json

import pytest

from core.mcp.server import build_email_mcp_server


def _call(server, name: str, arguments: dict) -> dict:
    result = asyncio.run(server.call_tool(name, arguments))
    return json.loads(result[0].text)


def test_mcp_server_exposes_send_email_tool():
    server = build_email_mcp_server({})
    tools = asyncio.run(server.list_tools())
    assert "send_email" in [t.name for t in tools]


def test_mcp_send_email_degrades_without_smtp():
    server = build_email_mcp_server({})
    data = _call(
        server,
        "send_email",
        {"recipient": "a@b.com", "subject": "hi", "body": "hello"},
    )
    assert data["sent"] is False
    assert "未配置" in data["reason"]


class DummySMTP:
    def __init__(self, host, port):
        self.host = host
        self.port = port

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def starttls(self):
        pass

    def login(self, user, password):
        assert user == "u@test"

    def send_message(self, msg):
        DummySMTP.last_msg = msg


def test_mcp_send_email_sends_when_configured(monkeypatch):
    monkeypatch.setattr("smtplib.SMTP", DummySMTP)
    server = build_email_mcp_server(
        {
            "SMTP_HOST": "smtp.test",
            "SMTP_PORT": 587,
            "SMTP_USER": "u@test",
            "SMTP_PASSWORD": "pw",
        }
    )
    data = _call(
        server,
        "send_email",
        {"recipient": "a@b.com", "subject": "hi", "body": "hello"},
    )
    assert data["sent"] is True
    assert data["to"] == "a@b.com"
    assert DummySMTP.last_msg["To"] == "a@b.com"


def test_in_process_tools_still_work():
    from core.mcp.tools import build_email_tools

    definitions, handlers = build_email_tools()
    assert "send_email" in [d["function"]["name"] for d in definitions]
    assert callable(handlers["send_email"])
