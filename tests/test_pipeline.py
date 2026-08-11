import json

from core.pipeline import run_pipeline
from tests.agent_stub import ScriptedClient

FINAL = {
    "status": "completed",
    "spam_check": {"is_invalid_lead": False, "reason": "ok"},
    "customer_profile": {"occupation_background": "运营", "core_pain_point": "转行",
                         "budget_sensitivity": "Medium", "deal_intent": "Medium",
                         "language_preference": "zh", "language_reason": "中文"},
    "compliance_report": {"verdict": "PASSED", "violations": [], "summary": "合规"},
    "email_draft": {"language": "zh", "subject": "跟进", "body": "您好"},
    "email_spam_risk": {"risk_level": "low", "issues": []},
}


def test_pipeline_completes_valid_lead():
    client = ScriptedClient([
        {"kind": "call", "tool": "check_spam", "args": {"chat": "x"}},
        {"kind": "final", "content": json.dumps(FINAL, ensure_ascii=False)},
    ])
    result = run_pipeline(client, "x")
    assert result.status == "completed"
    assert result.email_draft is not None


def test_pipeline_stops_on_invalid_lead():
    invalid = dict(FINAL)
    invalid.update({"status": "invalid_lead", "customer_profile": None,
                    "compliance_report": None, "email_draft": None, "email_spam_risk": None})
    invalid["spam_check"] = {"is_invalid_lead": True, "reason": "仅索要免费资料"}
    client = ScriptedClient([
        {"kind": "call", "tool": "check_spam", "args": {"chat": "x"}},
        {"kind": "final", "content": json.dumps(invalid, ensure_ascii=False)},
    ])
    result = run_pipeline(client, "x")
    assert result.status == "invalid_lead"
    assert result.email_draft is None
