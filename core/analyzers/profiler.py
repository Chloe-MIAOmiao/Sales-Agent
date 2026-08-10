from core.llm_client import LLMClient
from core.schemas import CustomerProfile


def analyze_profile(llm: LLMClient, chat_text: str) -> CustomerProfile:
    """从聊天记录提取 EduTech 客户画像与语言文化偏好。"""
    messages = [
        {
            "role": "user",
            "content": (
                "请分析以下销售聊天记录,提取客户画像。\n"
                "产品背景:售价 ¥2,999 的《数据分析与 AI 工具实战班》,4 周线上课程。\n"
                "画像要求:\n"
                "- occupation_background:客户职业背景与身份\n"
                "- core_pain_point:核心痛点(效率提升、转行等)\n"
                "- budget_sensitivity:围绕 ¥2,999 价格的预算敏感度 High/Medium/Low\n"
                "- deal_intent:成交意向度 High/Medium/Low\n"
                "- language_preference:zh(纯中文)/ en(纯英文)/ mixed(中英混杂或外企跨国背景)\n"
                "- language_reason:必须基于聊天记录的实际语言特征或客户自述背景,"
                "严禁根据人种或姓名主观猜测\n\n"
                f"聊天记录:\n{chat_text}"
            ),
        }
    ]
    return llm.complete_structured(messages, CustomerProfile)
