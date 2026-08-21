import json

import pytest

from tests.conftest import insert_valid_analysis, make_web_client
from core.schemas import (
    ComplianceReport,
    CustomerProfile,
    EmailDraft,
    EmailSpamRisk,
    PipelineResult,
    SpamCheck,
)


@pytest.fixture
def rep_client(tmp_path, monkeypatch):
    return make_web_client(tmp_path, monkeypatch, "rep", "rep", 1)


def _completed_result():
    return PipelineResult(
        status="completed",
        customer_profile=CustomerProfile(
            occupation_background="工程师",
            core_pain_point="效率低",
            budget_sensitivity="Medium",
            deal_intent="High",
            language_preference="zh",
            language_reason="客户使用中文",
        ),
        spam_check=SpamCheck(is_invalid_lead=False, reason="正常咨询"),
        compliance_report=ComplianceReport(verdict="PASSED", violations=[], summary="无违规"),
        email_draft=EmailDraft(language="zh", subject="跟进邮件", body="您好,感谢咨询……"),
        email_spam_risk=EmailSpamRisk(risk_level="low", issues=[]),
    )


def _invalid_result():
    return PipelineResult(
        status="invalid_lead",
        spam_check=SpamCheck(is_invalid_lead=True, reason="广告推销"),
    )


def _draft_count():
    from app import db

    conn = db.get_conn()
    try:
        return conn.execute("SELECT COUNT(*) FROM email_drafts").fetchone()[0]
    finally:
        conn.close()


def test_post_analysis_redirects_and_creates_one_draft(rep_client, monkeypatch):
    monkeypatch.setattr(
        "app.routes.analysis.run_pipeline",
        lambda llm, chat, lang="zh-CN": _completed_result(),
    )
    monkeypatch.setattr("app.routes.analysis.LLMClient", lambda: object())

    resp = rep_client.post(
        "/analysis",
        data={"chat_text": "客户:想了解课程", "customer_name": "张女士"},
        follow_redirects=False,
    )

    assert resp.status_code == 303
    assert resp.headers["location"].startswith("/analysis/result/")
    assert _draft_count() == 1


def test_refresh_result_page_does_not_duplicate_draft(rep_client, monkeypatch):
    monkeypatch.setattr(
        "app.routes.analysis.run_pipeline",
        lambda llm, chat, lang="zh-CN": _completed_result(),
    )
    monkeypatch.setattr("app.routes.analysis.LLMClient", lambda: object())
    resp = rep_client.post(
        "/analysis", data={"chat_text": "客户:想了解课程"}, follow_redirects=False
    )
    location = resp.headers["location"]

    first = rep_client.get(location)
    second = rep_client.get(location)

    assert first.status_code == 200
    assert second.status_code == 200
    assert "跟进邮件" in first.text
    assert "您好,感谢咨询……" in first.text
    assert "low" in first.text
    assert _draft_count() == 1


def test_result_page_denied_for_other_rep(tmp_path, monkeypatch):
    client = make_web_client(tmp_path, monkeypatch, "rep2", "rep", 2)
    from app import db

    conn = db.get_conn()
    analysis_id, _ = insert_valid_analysis(conn, created_by=1)
    conn.commit()
    conn.close()

    resp = client.get(f"/analysis/result/{analysis_id}", follow_redirects=False)

    assert resp.status_code == 303
    assert resp.headers["location"] != f"/analysis/result/{analysis_id}"


def test_manager_can_view_any_result_page(tmp_path, monkeypatch):
    client = make_web_client(tmp_path, monkeypatch, "mgr", "manager", 3)
    from app import db

    conn = db.get_conn()
    analysis_id, _ = insert_valid_analysis(conn, created_by=1)
    conn.commit()
    conn.close()

    resp = client.get(f"/analysis/result/{analysis_id}")

    assert resp.status_code == 200
    assert "跟进邮件" in resp.text


def test_post_invalid_lead_redirects_without_draft(rep_client, monkeypatch):
    monkeypatch.setattr(
        "app.routes.analysis.run_pipeline",
        lambda llm, chat, lang="zh-CN": _invalid_result(),
    )
    monkeypatch.setattr("app.routes.analysis.LLMClient", lambda: object())

    resp = rep_client.post(
        "/analysis", data={"chat_text": "加V买粉丝"}, follow_redirects=False
    )

    assert resp.status_code == 303
    assert resp.headers["location"].startswith("/analysis/result/")
    page = rep_client.get(resp.headers["location"])
    assert page.status_code == 200
    assert "广告推销" in page.text
    assert _draft_count() == 0


def test_legacy_row_without_email_spam_risk_renders(tmp_path, monkeypatch):
    client = make_web_client(tmp_path, monkeypatch, "rep", "rep", 1)
    from app import db

    conn = db.get_conn()
    analysis_id, _ = insert_valid_analysis(conn, created_by=1)
    conn.execute(
        "UPDATE analyses SET email_spam_risk_json = NULL WHERE id = ?", (analysis_id,)
    )
    conn.commit()
    conn.close()

    resp = client.get(f"/analysis/result/{analysis_id}")

    assert resp.status_code == 200
    assert "跟进邮件" in resp.text


def test_analyses_table_has_email_spam_risk_column(tmp_path, monkeypatch):
    make_web_client(tmp_path, monkeypatch, "rep", "rep", 1)
    from app import db

    conn = db.get_conn()
    cols = [r[1] for r in conn.execute("PRAGMA table_info(analyses)")]
    conn.close()
    assert "email_spam_risk_json" in cols


def test_persisted_email_spam_risk_roundtrips(rep_client, monkeypatch):
    captured = {}

    def fake_pipeline(llm, chat, lang="zh-CN"):
        captured["risk"] = EmailSpamRisk(risk_level="high", issues=["夸大收益"])
        result = _completed_result()
        result.email_spam_risk = captured["risk"]
        return result

    monkeypatch.setattr("app.routes.analysis.run_pipeline", fake_pipeline)
    monkeypatch.setattr("app.routes.analysis.LLMClient", lambda: object())
    resp = rep_client.post(
        "/analysis", data={"chat_text": "客户:想了解课程"}, follow_redirects=False
    )
    location = resp.headers["location"]

    from app import db

    conn = db.get_conn()
    row = conn.execute(
        "SELECT email_spam_risk_json FROM analyses ORDER BY id DESC LIMIT 1"
    ).fetchone()
    conn.close()
    stored = json.loads(row["email_spam_risk_json"])
    assert stored["risk_level"] == "high"

    page = rep_client.get(location)
    assert "high" in page.text
