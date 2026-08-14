import json

from core.agent import TOOL_DEFINITIONS, run_agent
from core.schemas import PipelineResult
from tests.agent_stub import ScriptedClient


def test_tool_definitions_cover_required_tools():
    names = {t["function"]["name"] for t in TOOL_DEFINITIONS}
    for required in ["analyze_profile", "audit_compliance", "check_spam", "generate_email", "check_email_spam"]:
        assert required in names


def test_run_agent_returns_completed_result():
    client = ScriptedClient([
        {"kind": "call", "tool": "check_spam", "args": {"chat": "x"}},
        {"kind": "call", "tool": "analyze_profile", "args": {"chat": "x"}},
        {"kind": "call", "tool": "audit_compliance", "args": {"chat": "x"}},
        {"kind": "call", "tool": "generate_email", "args": {"chat": "x"}},
        {"kind": "call", "tool": "check_email_spam", "args": {"chat": "x"}},
        {"kind": "final", "content": json.dumps({})},
    ])
    result = run_agent(client, "x")
    assert isinstance(result, PipelineResult)
    assert result.status == "completed"
    assert result.customer_profile is not None
    assert result.email_draft is not None


def test_run_agent_invalid_lead():
    from core.schemas import SpamCheck
    client = ScriptedClient(
        [{"kind": "call", "tool": "check_spam", "args": {"chat": "x"}}],
        structured={SpamCheck: SpamCheck(is_invalid_lead=True, reason="仅索要免费资料")},
    )
    result = run_agent(client, "x")
    assert result.status == "invalid_lead"
    assert result.customer_profile is None


from core import agent


def test_get_system_prompt_default_is_chinese():
    sys, tools = agent.get_system_prompt("zh-CN")
    assert "数据分析" in sys
    assert tools[0]["function"]["name"] == "check_spam"


def test_get_system_prompt_english():
    sys, tools = agent.get_system_prompt("en-US")
    assert "compliance" in sys.lower() or "agent" in sys.lower()
    assert len(tools) == 5


def test_get_system_prompt_invalid_falls_back():
    sys, _ = agent.get_system_prompt("fr-FR")
    assert "数据分析" in sys