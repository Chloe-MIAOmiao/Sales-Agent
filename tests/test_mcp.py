from core.mcp.email_server import EmailServer


def test_send_email_degrades_when_no_smtp():
    server = EmailServer({})
    result = server.send_email("a@b.com", "hi", "body")
    assert result["sent"] is False
    assert "SMTP" in result["reason"] or "未配置" in result["reason"]


def test_list_inbox_empty_without_imap():
    server = EmailServer({})
    assert server.list_inbox() == []
