import pytest

from core.llm_client import LLMClient


class FakeLLMClient(LLMClient):
    """返回预设结构化结果的假客户端,不发起真实网络请求。"""

    def __init__(self):
        self.responses: dict[type, object] = {}
        self.calls: list[dict] = []

    def complete_structured(
        self, messages, response_model, temperature=0.1, max_retries=2
    ):
        self.calls.append({"messages": messages, "model": response_model})
        if response_model not in self.responses:
            raise AssertionError(f"未为 {response_model.__name__} 预设响应")
        value = self.responses[response_model]
        if isinstance(value, response_model):
            return value
        return response_model.model_validate(value)

    def expect(self, response_model, value):
        self.responses[response_model] = value
        return self


@pytest.fixture
def fake_llm():
    return FakeLLMClient()


def make_web_client(tmp_path, monkeypatch, username, role, uid):
    """初始化临时数据库并返回带指定用户会话的 TestClient。"""
    from starlette.testclient import TestClient

    from app import db
    from app.auth import create_session_token
    from app.main import app

    monkeypatch.setattr(db, "DB_PATH", tmp_path / "web.db")
    db.init_db()
    conn = db.get_conn()
    for seed_name, seed_role in (("rep", "rep"), ("rep2", "rep"), ("mgr", "manager")):
        conn.execute(
            "INSERT OR IGNORE INTO users (username, password_hash, role) VALUES (?, 'x', ?)",
            (seed_name, seed_role),
        )
    conn.commit()
    conn.close()
    token = create_session_token(uid, username, role)
    return TestClient(app, cookies={"session": token})


def insert_valid_analysis(conn, created_by=1):
    """直接插入一条完整分析 + 草稿,返回 (analysis_id, draft_id)。"""
    cur = conn.execute(
        "INSERT INTO customers (name, language, source_chat, stage, owner_id)"
        " VALUES ('张女士', 'zh', '聊天内容', 'leads', ?)",
        (created_by,),
    )
    customer_id = cur.lastrowid
    cur = conn.execute(
        "INSERT INTO analyses (customer_id, created_by, profile_json, compliance_json,"
        " spam_json, email_spam_risk_json, verdict) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            customer_id,
            created_by,
            '{"occupation_background":"工程师","core_pain_point":"效率低",'
            '"budget_sensitivity":"Medium","deal_intent":"High",'
            '"language_preference":"zh","language_reason":"客户使用中文"}',
            '{"verdict":"PASSED","violations":[],"summary":"无违规"}',
            '{"is_invalid_lead":false,"reason":"正常咨询"}',
            '{"risk_level":"low","issues":[]}',
            "PASSED",
        ),
    )
    analysis_id = cur.lastrowid
    cur = conn.execute(
        "INSERT INTO email_drafts (analysis_id, subject, body, language, created_by)"
        " VALUES (?, '跟进邮件', '您好,感谢咨询……', 'zh', ?)",
        (analysis_id, created_by),
    )
    return analysis_id, cur.lastrowid
