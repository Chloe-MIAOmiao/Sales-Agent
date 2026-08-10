from core.llm_client import LLMClient
from core.schemas import EmailDraft, EmailSpamRisk, SpamCheck


def check_invalid_lead(llm: LLMClient, chat_text: str) -> SpamCheck:
    messages = [
        {
            "role": "user",
            "content": (
                "请判断以下聊天记录是否为无效/垃圾线索。\n"
                "无效线索特征:仅索要免费资料、无购买意向、广告刷屏、机器人消息、"
                "无意义的乱码或重复内容。\n"
                "若有明确学习需求或咨询课程信息,则判定为有效线索。\n\n"
                f"聊天记录:\n{chat_text}"
            ),
        }
    ]
    return llm.complete_structured(messages, SpamCheck)


def check_email_spam(llm: LLMClient, draft: EmailDraft) -> EmailSpamRisk:
    messages = [
        {
            "role": "user",
            "content": (
                "请评估以下邮件草稿被邮箱系统判定为垃圾邮件(SPAM)的风险。\n"
                "风险因素:大量全大写单词、过多感叹号、促销词(如 FREE/LIMITED)、"
                "可疑链接、诱导性标题等。\n"
                "risk_level 取 low / medium / high,并在 issues 中列出具体问题。\n\n"
                f"邮件主题:\n{draft.subject}\n\n邮件正文:\n{draft.body}"
            ),
        }
    ]
    return llm.complete_structured(messages, EmailSpamRisk)
