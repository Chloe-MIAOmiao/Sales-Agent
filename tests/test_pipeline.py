from core.pipeline import run_pipeline
from core.schemas import (
    ComplianceReport,
    CustomerProfile,
    EmailDraft,
    EmailSpamRisk,
    LanguagePreference,
    SpamCheck,
)


def test_pipeline_completes_valid_lead(fake_llm):
    fake_llm.expect(SpamCheck, SpamCheck(is_invalid_lead=False, reason="有效"))
    fake_llm.expect(
        CustomerProfile,
        CustomerProfile(
            occupation_background="运营",
            core_pain_point="转行",
            budget_sensitivity="Medium",
            deal_intent="Medium",
            language_preference=LanguagePreference.ZH,
            language_reason="中文聊天",
        ),
    )
    fake_llm.expect(ComplianceReport, ComplianceReport(verdict="PASSED", violations=[], summary="无违规"))
    fake_llm.expect(
        EmailDraft,
        EmailDraft(language="zh", subject="跟进", body="您好"),
    )
    fake_llm.expect(EmailSpamRisk, EmailSpamRisk(risk_level="low", issues=[]))
    fake_llm.expect(ComplianceReport, ComplianceReport(verdict="PASSED", violations=[], summary="合规"))

    result = run_pipeline(fake_llm, "客户:这个课程多少钱?")
    assert result.status == "completed"
    assert result.customer_profile is not None
    assert result.email_draft is not None
    assert result.email_draft.language == "zh"
    assert result.email_spam_risk is not None
    assert result.compliance_report is not None


def test_pipeline_stops_on_invalid_lead(fake_llm):
    fake_llm.expect(
        SpamCheck,
        SpamCheck(is_invalid_lead=True, reason="仅索要免费资料"),
    )
    result = run_pipeline(fake_llm, "给我免费资料")
    assert result.status == "invalid_lead"
    assert result.email_draft is None
    assert result.customer_profile is None
