from core.analyzers.email_writer import write_followup_email
from core.schemas import ComplianceReport, CustomerProfile, EmailDraft, LanguagePreference


def _profile(lang: LanguagePreference) -> CustomerProfile:
    return CustomerProfile(
        occupation_background="传统行业运营",
        core_pain_point="想转行数据分析",
        budget_sensitivity="High",
        deal_intent="Medium",
        language_preference=lang,
        language_reason="聊天记录为中文",
    )


def test_email_language_follows_profile(fake_llm):
    fake_llm.expect(
        EmailDraft,
        EmailDraft(
            language="zh",
            subject="数据分析实战班跟进",
            body="尊敬的客户,您好!",
        ),
    )
    draft = write_followup_email(
        fake_llm, _profile(LanguagePreference.ZH), ComplianceReport(verdict="PASSED", violations=[], summary=""), "聊天记录"
    )
    assert draft.language == "zh"
    assert "数据分析实战班跟进" == draft.subject


def test_email_english_for_foreign_company_client(fake_llm):
    fake_llm.expect(
        EmailDraft,
        EmailDraft(
            language="en",
            subject="Data Analytics & AI Tools Bootcamp Follow-up",
            body="Dear Ms. Zhang,",
        ),
    )
    draft = write_followup_email(
        fake_llm, _profile(LanguagePreference.EN), ComplianceReport(verdict="PASSED", violations=[], summary=""), "chat"
    )
    assert draft.language == "en"


def test_email_prompt_includes_compliance_correction(fake_llm):
    fake_llm.expect(
        EmailDraft,
        EmailDraft(language="zh", subject="跟进", body="课程提供 1 对 1 简历辅导与项目履历打磨"),
    )
    violations = [
        {
            "violation_type": "保底薪资",
            "quote": "学完保底年薪 15 万",
        }
    ]
    report = ComplianceReport(verdict="WARNING", violations=violations, summary="违规")
    write_followup_email(fake_llm, _profile(LanguagePreference.ZH), report, "聊天记录")
    sent_messages = fake_llm.calls[-1]["messages"]
    combined = " ".join(m["content"] for m in sent_messages)
    assert "保底薪资" in combined
    assert "简历辅导" in combined
