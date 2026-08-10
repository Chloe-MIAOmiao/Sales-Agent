import json

from core.llm_client import LLMClient
from core.schemas import ComplianceReport, CustomerProfile, EmailDraft


def write_followup_email(
    llm: LLMClient,
    profile: CustomerProfile,
    compliance_report: ComplianceReport,
    chat_text: str,
) -> EmailDraft:
    lang_hint = {
        "zh": "生成纯中文跟进邮件",
        "en": "生成全英文跟进邮件",
        "mixed": "生成中英双语跟进邮件",
    }[profile.language_preference.value]

    correction_notes = ""
    if compliance_report.violations:
        items = "\n".join(
            f"- 违规: {v.violation_type}, 原句: {v.quote}"
            for v in compliance_report.violations
        )
        correction_notes = (
            "微信聊天中存在以下违规承诺,邮件中必须修正为合规表达"
            "(例如将'保底就业'改写为'提供 1 对 1 简历辅导与项目履历打磨',"
            "禁止出现保证就业/保底薪资/包学会/拒绝退款/虚假稀缺):\n" + items
        )

    messages = [
        {
            "role": "user",
            "content": (
                "你是高级销售总监,请为 EduTech 课程《数据分析与 AI 工具实战班》"
                "(售价 ¥2,999,4 周线上课程)写一封跟进邮件。\n"
                f"邮件语言: {lang_hint}(严格基于客户画像中的语言偏好,"
                "不要根据人种或姓名猜测)。\n"
                "产品卖点:零基础友好、4 周实战项目、AI 工具实操。\n"
                f"客户画像:\n{json.dumps(profile.model_dump(), ensure_ascii=False)}\n\n"
                f"{correction_notes}\n"
                "要求:专业、克制、无违规承诺,安抚客户顾虑,邀请进一步沟通。\n\n"
                f"原始聊天记录:\n{chat_text}"
            ),
        }
    ]
    return llm.complete_structured(messages, EmailDraft)
