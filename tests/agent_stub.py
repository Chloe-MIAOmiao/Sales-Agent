from core.schemas import ComplianceReport, CustomerProfile, EmailDraft, EmailSpamRisk, SpamCheck

_DEFAULTS = {
    SpamCheck: lambda: SpamCheck(is_invalid_lead=False, reason="ok"),
    CustomerProfile: lambda: CustomerProfile(
        occupation_background="运营", core_pain_point="转行",
        budget_sensitivity="Medium", deal_intent="Medium",
        language_preference="zh", language_reason="中文",
    ),
    ComplianceReport: lambda: ComplianceReport(verdict="PASSED", violations=[], summary="合规"),
    EmailDraft: lambda: EmailDraft(language="zh", subject="跟进", body="您好"),
    EmailSpamRisk: lambda: EmailSpamRisk(risk_level="low", issues=[]),
}


class ScriptedClient:
    """可编程 LLM 桩:回放工具调用与最终答案序列,并支持结构化输出默认值。"""

    def __init__(self, sequence, structured=None):
        self.sequence = list(sequence)
        self.i = 0
        self.structured = structured or {}

    def complete_tool_loop(self, messages, tools, execute, max_steps=8, temperature=0.3):
        steps = 0
        while steps < max_steps and self.i < len(self.sequence):
            item = self.sequence[self.i]
            self.i += 1
            steps += 1
            if item["kind"] == "call":
                obs = execute(item["tool"], item["args"])
                self.sequence.insert(self.i, {"kind": "obs", "content": obs})
            elif item["kind"] == "obs":
                continue
            else:
                return {"final": item["content"], "steps": steps}
        return {"final": "", "steps": steps, "timeout": True}

    def complete_structured(self, messages, response_model, temperature=0.1, max_retries=2):
        if response_model in self.structured:
            return self.structured[response_model]
        if response_model in _DEFAULTS:
            return _DEFAULTS[response_model]()
        raise NotImplementedError(f"ScriptedClient 未支持 {response_model.__name__}")
