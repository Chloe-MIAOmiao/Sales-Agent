from mcp.server.fastmcp import FastMCP

from core.mcp.email_server import EmailServer


def build_email_mcp_server(config: dict | None = None) -> FastMCP:
    email = EmailServer(config)
    server: FastMCP = FastMCP("sales-agent-email")

    @server.tool()
    def send_email(recipient: str, subject: str, body: str) -> dict:
        """发送合规跟进邮件(需人工批准后调用);未配置 SMTP 时安全降级。"""
        return email.send_email(recipient, subject, body)

    return server


if __name__ == "__main__":
    build_email_mcp_server().run()
