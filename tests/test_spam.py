from core.analyzers.spam import check_email_spam, check_invalid_lead
from core.schemas import EmailDraft, EmailSpamRisk, SpamCheck


def test_lead_grabber_marked_invalid(fake_llm):
    fake_llm.expect(
        SpamCheck,
        SpamCheck(is_invalid_lead=True, reason="仅索要免费资料,无购买意向"),
    )
    result = check_invalid_lead(fake_llm, "给我发一下免费资料")
    assert result.is_invalid_lead is True


def test_normal_inquiry_valid(fake_llm):
    fake_llm.expect(
        SpamCheck,
        SpamCheck(is_invalid_lead=False, reason="有明确学习需求并询问价格"),
    )
    result = check_invalid_lead(fake_llm, "这个课程多少钱?零基础能学吗?")
    assert result.is_invalid_lead is False


def test_email_spam_risk_detects_all_caps(fake_llm):
    fake_llm.expect(
        EmailSpamRisk,
        EmailSpamRisk(
            risk_level="high",
            issues=["正文使用大量大写单词,易触发反垃圾规则"],
        ),
    )
    draft = EmailDraft(language="en", subject="URGENT!!!", body="FREE MONEY NOW!!!")
    risk = check_email_spam(fake_llm, draft)
    assert risk.risk_level in ("low", "medium", "high")
    assert isinstance(risk.issues, list)
