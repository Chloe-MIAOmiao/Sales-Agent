from core.schemas import ComplianceReport, CustomerProfile, LanguagePreference
from core.tasks import maybe_create_followup_task


def _profile(deal_intent: str) -> CustomerProfile:
    return CustomerProfile(
        occupation_background="运营", core_pain_point="转行",
        budget_sensitivity="Medium", deal_intent=deal_intent,
        language_preference=LanguagePreference.ZH, language_reason="中文",
    )


def _conn(tmp_path):
    from app import db
    orig = db.DB_PATH
    db.DB_PATH = tmp_path / "t.db"
    db.init_db()
    conn = db.get_conn()
    conn.execute("INSERT INTO users (username, password_hash, role) VALUES ('rep','x','rep')")
    conn.execute("INSERT INTO customers (name) VALUES ('张女士')")
    conn.execute("INSERT INTO analyses (customer_id, created_by, verdict) VALUES (1,1,'WARNING')")
    conn.commit()
    return conn


def test_creates_task_on_warning(tmp_path):
    conn = _conn(tmp_path)
    task_id = maybe_create_followup_task(
        conn, analysis_id=1, customer_id=1, user_id=1,
        profile=_profile("Medium"),
        compliance=ComplianceReport(verdict="WARNING", violations=[], summary="s"),
    )
    assert task_id is not None
    row = conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
    assert row["status"] == "pending"
    conn.close()


def test_creates_task_on_high_intent(tmp_path):
    conn = _conn(tmp_path)
    task_id = maybe_create_followup_task(
        conn, analysis_id=1, customer_id=1, user_id=1,
        profile=_profile("High"),
        compliance=ComplianceReport(verdict="PASSED", violations=[], summary="s"),
    )
    assert task_id is not None
    conn.close()


def test_no_task_when_passed_and_medium(tmp_path):
    conn = _conn(tmp_path)
    task_id = maybe_create_followup_task(
        conn, analysis_id=1, customer_id=1, user_id=1,
        profile=_profile("Medium"),
        compliance=ComplianceReport(verdict="PASSED", violations=[], summary="s"),
    )
    assert task_id is None
    conn.close()
