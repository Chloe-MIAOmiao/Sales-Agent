import json

from core.agent import TOOL_DEFINITIONS, run_agent
from core.schemas import PipelineResult
from tests.agent_stub import ScriptedClient


def test_tool_definitions_cover_required_tools():
    names = {t["function"]["name"] for t in TOOL_DEFINITIONS}
    for required in ["analyze_profile", "audit_compliance", "check_spam", "generate_email", "check_email_spam"]:
        assert required in names


def test_run_agent_returns_completed_result():
    result_json = json.dumps({
        "status": "completed",
        "spam_check": {"is_invalid_lead": False, "reason": "ok"},
        "customer_profile": {"occupation_background": "运营", "core_pain_point": "转行",
                             "budget_sensitivity": "Medium", "deal_intent": "Medium",
                             "language_preference": "zh", "language_reason": "中文"},
        "compliance_report": {"verdict": "PASSED", "violations": [], "summary": "合规"},
        "email_draft": {"language": "zh", "subject": "跟进", "body": "您好"},
        "email_spam_risk": {"risk_level": "low", "issues": []},
    })
    client = ScriptedClient([
        {"kind": "call", "tool": "check_spam", "args": {"chat": "x"}},
        {"kind": "final", "content": result_json},
    ])
    result = run_agent(client, "x")
    assert isinstance(result, PipelineResult)
    assert result.status == "completed"
