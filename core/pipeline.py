from core.analyzers.compliance import audit_chat, audit_email
from core.analyzers.email_writer import write_followup_email
from core.analyzers.profiler import analyze_profile
from core.analyzers.spam import check_email_spam, check_invalid_lead
from core.llm_client import LLMClient
from core.schemas import PipelineResult


def run_pipeline(llm: LLMClient, chat_text: str) -> PipelineResult:
    """执行完整分析流水线:无效线索 → 画像 → 合规审计 → 邮件生成 → 邮件复查。"""
    # Step 1: 无效线索识别,命中即终止
    spam_check = check_invalid_lead(llm, chat_text)
    if spam_check.is_invalid_lead:
        return PipelineResult(status="invalid_lead", spam_check=spam_check)

    # Step 2: 客户画像
    profile = analyze_profile(llm, chat_text)

    # Step 3: 合规审计(聊天记录)
    chat_compliance = audit_chat(llm, chat_text)

    # Step 4: 生成合规邮件(语言自适应 + 违规修正)
    draft = write_followup_email(llm, profile, chat_compliance, chat_text)

    # Step 5: 邮件复查(反垃圾 + 合规)
    email_spam_risk = check_email_spam(llm, draft)
    email_compliance = audit_email(llm, draft)

    return PipelineResult(
        status="completed",
        spam_check=spam_check,
        customer_profile=profile,
        compliance_report=chat_compliance,
        email_draft=draft,
        email_spam_risk=email_spam_risk,
    )
