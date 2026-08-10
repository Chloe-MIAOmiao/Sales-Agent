from core.llm_client import LLMClient
from core.schemas import ComplianceReport, EmailDraft

RED_LINE_RULES = [
    "保证就业",
    "保底薪资",
    "保底年薪",
    "包学会",
    "100% 学会",
    "拒绝退款",
    "仅剩最后一个名额",
    "虚假稀缺",
]


def _red_line_hint() -> str:
    return (
        "培训行业合规红线(检查销售/邮件中是否出现):\n"
        + "\n".join(f"- {r}" for r in RED_LINE_RULES)
        + "\n若出现任一违规,verdict 必须为 WARNING,并给出 violation_type 与违规原句 quote。"
    )


def audit_chat(llm: LLMClient, chat_text: str) -> ComplianceReport:
    messages = [
        {
            "role": "user",
            "content": (
                "请对以下销售聊天记录做合规风险审计。\n" + _red_line_hint() + f"\n\n聊天记录:\n{chat_text}"
            ),
        }
    ]
    return llm.complete_structured(messages, ComplianceReport)


def audit_email(llm: LLMClient, draft: EmailDraft) -> ComplianceReport:
    messages = [
        {
            "role": "user",
            "content": (
                "请对以下待发送的邮件草稿做合规复查,确保不出现培训行业违规承诺。\n"
                + _red_line_hint()
                + f"\n\n邮件主题:\n{draft.subject}\n\n邮件正文:\n{draft.body}"
            ),
        }
    ]
    return llm.complete_structured(messages, ComplianceReport)
