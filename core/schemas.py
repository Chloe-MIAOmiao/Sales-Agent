from enum import Enum

from pydantic import BaseModel, Field


class LanguagePreference(str, Enum):
    ZH = "zh"
    EN = "en"
    MIXED = "mixed"


class CustomerProfile(BaseModel):
    occupation_background: str = Field(description="客户的职业背景与身份")
    core_pain_point: str = Field(description="客户的核心痛点(如效率瓶颈、转行需求)")
    budget_sensitivity: str = Field(description="预算敏感度,必须是 High / Medium / Low")
    deal_intent: str = Field(description="成交意向度,必须是 High / Medium / Low")
    language_preference: LanguagePreference = Field(
        description="邮件语言偏好:zh 纯中文 / en 纯英文 / mixed 中英双语"
    )
    language_reason: str = Field(
        description="判断语言偏好的依据,必须是聊天记录中的实际语言特征或客户自述背景"
    )


class ComplianceViolation(BaseModel):
    violation_type: str = Field(description="违规类型,如 包学会 / 保底薪资 / 虚假稀缺 / 拒绝退款")
    quote: str = Field(description="聊天记录中具体的违规原句")


class ComplianceReport(BaseModel):
    verdict: str = Field(description="审计结论,必须是 PASSED 或 WARNING")
    violations: list[ComplianceViolation] = Field(default_factory=list)
    summary: str = Field(description="审计摘要")


class SpamCheck(BaseModel):
    is_invalid_lead: bool = Field(description="是否判定为无效/垃圾线索")
    reason: str = Field(description="判定依据")


class EmailSpamRisk(BaseModel):
    risk_level: str = Field(description="邮件反垃圾风险等级,必须是 low / medium / high")
    issues: list[str] = Field(default_factory=list)


class EmailDraft(BaseModel):
    language: LanguagePreference = Field(description="邮件使用的语言")
    subject: str = Field(description="邮件主题")
    body: str = Field(description="邮件正文")


class EmailAudit(BaseModel):
    draft: EmailDraft
    spam_risk: EmailSpamRisk
    compliance_report: ComplianceReport


class PipelineResult(BaseModel):
    status: str = Field(description="pipeline 状态:invalid_lead / completed / error")
    customer_profile: CustomerProfile | None = None
    spam_check: SpamCheck | None = None
    compliance_report: ComplianceReport | None = None
    email_draft: EmailDraft | None = None
    email_spam_risk: EmailSpamRisk | None = None
    error_message: str | None = None
