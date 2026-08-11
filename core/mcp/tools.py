from core.mcp.email_server import EmailServer

EMAIL_TOOL_DEFINITIONS = [
    {"type": "function", "function": {"name": "send_email", "description": "发送合规跟进邮件(需人工批准后调用)", "parameters": {"type": "object", "properties": {"recipient": {"type": "string"}, "subject": {"type": "string"}, "body": {"type": "string"}}, "required": ["recipient", "subject", "body"]}}},
]


def build_email_tools() -> tuple[list, dict]:
    server = EmailServer()
    return EMAIL_TOOL_DEFINITIONS, {
        "send_email": lambda recipient, subject, body: server.send_email(recipient, subject, body),
    }
