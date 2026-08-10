from core.analyzers.compliance import audit_chat, audit_email
from core.schemas import ComplianceReport, ComplianceViolation, EmailDraft


def test_audit_chat_flags_guaranteed_salary(fake_llm):
    fake_llm.expect(
        ComplianceReport,
        ComplianceReport(
            verdict="WARNING",
            violations=[
                ComplianceViolation(
                    violation_type="保底薪资",
                    quote="学完保底年薪 15 万",
                )
            ],
            summary="销售存在保底薪资承诺",
        ),
    )
    report = audit_chat(fake_llm, "我们保证学完保底年薪 15 万")
    assert report.verdict == "WARNING"
    assert any(v.violation_type == "保底薪资" for v in report.violations)


def test_audit_chat_clean_passes(fake_llm):
    fake_llm.expect(
        ComplianceReport,
        ComplianceReport(verdict="PASSED", violations=[], summary="无违规"),
    )
    report = audit_chat(fake_llm, "课程提供 1 对 1 简历辅导")
    assert report.verdict == "PASSED"
    assert report.violations == []


def test_audit_email_checks_generated_draft(fake_llm):
    fake_llm.expect(
        ComplianceReport,
        ComplianceReport(
            verdict="WARNING",
            violations=[
                ComplianceViolation(
                    violation_type="包学会",
                    quote="保证 100% 学会",
                )
            ],
            summary="邮件中出现包学会承诺",
        ),
    )
    draft = EmailDraft(
        language="zh", subject="跟进", body="我们保证 100% 学会数据分析"
    )
    report = audit_email(fake_llm, draft)
    assert report.verdict == "WARNING"
    assert any(v.violation_type == "包学会" for v in report.violations)
