import json

from core.analyzers.compliance import audit_chat
from core.analyzers.email_writer import write_followup_email
from core.analyzers.profiler import analyze_profile
from core.analyzers.spam import check_email_spam, check_invalid_lead
from core.llm_client import LLMClient
from core.schemas import PipelineResult

AGENT_DEFAULT_LANG = "zh-CN"
_AGENT_LANGS = {"zh-CN", "zh-HK", "en-US"}

_AGENT_SYSTEM_PROMPTS = {
    "zh-CN": (
        "你是 EduTech《数据分析与 AI 工具实战班》(售价 ¥2,999,4 周线上课程)的销售合规 Agent。\n"
        "合规红线:严禁保证就业、保底薪资、包学会、拒绝退款、虚假稀缺。\n"
        "流程:先用 check_spam 判断线索有效性;有效则用 analyze_profile 提取画像,"
        "用 audit_compliance 审计聊天合规性,再用 generate_email 生成合规邮件(语言跟随客户画像),"
        "最后用 check_email_spam 复查。工具观察结果请基于聊天记录推理,最终只输出一个符合 PipelineResult 的 JSON。"
    ),
    "zh-HK": (
        "你是 EduTech《數據分析與 AI 工具實戰班》(售價 ¥2,999,4 週線上課程)的銷售合規 Agent。\n"
        "合規紅線:嚴禁保證就業、保底薪資、包學會、拒絕退款、虛假稀缺。\n"
        "流程:先用 check_spam 判斷線索有效性;有效則用 analyze_profile 提取畫像,"
        "用 audit_compliance 審計聊天合規性,再用 generate_email 生成合規郵件(語言跟隨客戶畫像),"
        "最後用 check_email_spam 複查。工具觀察結果請基於聊天記錄推理,最終只輸出一個符合 PipelineResult 的 JSON。"
    ),
    "en-US": (
        "You are the sales-compliance Agent for EduTech's \"Data Analytics & AI Tools Bootcamp\" "
        "(price ¥2,999, 4-week online course).\n"
        "Compliance red lines: NO guaranteed employment, NO minimum-salary promises, NO \"100% learned\" claims, "
        "NO refusing refunds, and NO creating false scarcity.\n"
        "Flow: first call check_spam to decide if the lead is valid; if valid, extract a profile with "
        "analyze_profile, audit the chat with audit_compliance, then generate a compliant follow-up email "
        "with generate_email (language follows the customer profile), and finally re-check the email with "
        "check_email_spam. Reason about tool observations from the chat record; return exactly one JSON "
        "matching the PipelineResult schema."
    ),
}

_TOOL_DESCRIPTIONS = {
    "check_spam": {
        "zh-CN": "判断聊天是否为无效线索",
        "zh-HK": "判斷聊天是否為無效線索",
        "en-US": "Decide whether the chat is an invalid/spam lead",
    },
    "analyze_profile": {
        "zh-CN": "提取客户画像",
        "zh-HK": "提取客戶畫像",
        "en-US": "Extract the customer profile",
    },
    "audit_compliance": {
        "zh-CN": "审计聊天记录合规风险",
        "zh-HK": "審計聊天記錄合規風險",
        "en-US": "Audit the chat record for compliance risks",
    },
    "generate_email": {
        "zh-CN": "生成合规跟进邮件",
        "zh-HK": "生成合規跟進郵件",
        "en-US": "Generate a compliant follow-up email",
    },
    "check_email_spam": {
        "zh-CN": "检查邮件反垃圾风险",
        "zh-HK": "檢查郵件反垃圾風險",
        "en-US": "Check the email for spam risk",
    },
}

_BASE_TOOL_NAMES = [
    "check_spam", "analyze_profile", "audit_compliance", "generate_email", "check_email_spam",
]


def _resolve_lang(lang):
    return lang if lang in _AGENT_LANGS else AGENT_DEFAULT_LANG


def get_system_prompt(lang="zh-CN"):
    lang = _resolve_lang(lang)
    system = _AGENT_SYSTEM_PROMPTS[lang]
    tools = [
        {
            "type": "function",
            "function": {
                "name": name,
                "description": _TOOL_DESCRIPTIONS[name][lang],
                "parameters": {"type": "object", "properties": {"chat": {"type": "string"}}, "required": ["chat"]},
            },
        }
        for name in _BASE_TOOL_NAMES
    ]
    return system, tools


SYSTEM_PROMPT = (
    "你是 EduTech《数据分析与 AI 工具实战班》(售价 ¥2,999,4 周线上课程)的销售合规 Agent。\n"
    "合规红线:严禁保证就业、保底薪资、包学会、拒绝退款、虚假稀缺。\n"
    "流程:先用 check_spam 判断线索有效性;有效则用 analyze_profile 提取画像,"
    "用 audit_compliance 审计聊天合规性,再用 generate_email 生成合规邮件(语言跟随客户画像),"
    "最后用 check_email_spam 复查。工具观察结果请基于聊天记录推理,最终只输出一个符合 PipelineResult 的 JSON。"
)

TOOL_DEFINITIONS = [
    {"type": "function", "function": {"name": "check_spam", "description": "判断聊天是否为无效线索", "parameters": {"type": "object", "properties": {"chat": {"type": "string"}}, "required": ["chat"]}}},
    {"type": "function", "function": {"name": "analyze_profile", "description": "提取客户画像", "parameters": {"type": "object", "properties": {"chat": {"type": "string"}}, "required": ["chat"]}}},
    {"type": "function", "function": {"name": "audit_compliance", "description": "审计聊天记录合规风险", "parameters": {"type": "object", "properties": {"chat": {"type": "string"}}, "required": ["chat"]}}},
    {"type": "function", "function": {"name": "generate_email", "description": "生成合规跟进邮件", "parameters": {"type": "object", "properties": {"chat": {"type": "string"}}, "required": ["chat"]}}},
    {"type": "function", "function": {"name": "check_email_spam", "description": "检查邮件反垃圾风险", "parameters": {"type": "object", "properties": {"chat": {"type": "string"}}, "required": ["chat"]}}},
]


def _make_executor(llm: LLMClient):
    """返回可执行工具函数;状态保存在闭包中,供最终组装 PipelineResult。"""
    state: dict = {}

    def _check_spam(chat: str):
        state["spam"] = check_invalid_lead(llm, chat)
        return state["spam"].model_dump_json(ensure_ascii=False)

    def _analyze_profile(chat: str):
        state["profile"] = analyze_profile(llm, chat)
        return state["profile"].model_dump_json(ensure_ascii=False)

    def _audit_compliance(chat: str):
        state["compliance"] = audit_chat(llm, chat)
        return state["compliance"].model_dump_json(ensure_ascii=False)

    def _generate_email(chat: str):
        profile = state.get("profile")
        compliance = state.get("compliance")
        if profile is None or compliance is None:
            raise RuntimeError("generate_email 需先执行 analyze_profile 与 audit_compliance")
        state["draft"] = write_followup_email(llm, profile, compliance, chat)
        return state["draft"].model_dump_json(ensure_ascii=False)

    def _check_email_spam(chat: str):
        draft = state.get("draft")
        if draft is None:
            raise RuntimeError("check_email_spam 需先执行 generate_email")
        state["spam_risk"] = check_email_spam(llm, draft)
        return state["spam_risk"].model_dump_json(ensure_ascii=False)

    registry = {
        "check_spam": _check_spam,
        "analyze_profile": _analyze_profile,
        "audit_compliance": _audit_compliance,
        "generate_email": _generate_email,
        "check_email_spam": _check_email_spam,
    }
    return registry, state


REGISTRY_NAMES = {
    "check_spam": "spam",
    "analyze_profile": "profile",
    "audit_compliance": "compliance",
    "generate_email": "draft",
    "check_email_spam": "spam_risk",
}

_REQUIRED_ORDER = ["check_spam", "analyze_profile", "audit_compliance", "generate_email", "check_email_spam"]
_STATE_KEY = REGISTRY_NAMES


def run_agent(llm: LLMClient, chat_text: str, lang: str = AGENT_DEFAULT_LANG):
    system_prompt, tools = get_system_prompt(lang)
    registry, state = _make_executor(llm)
    llm.complete_tool_loop(
        messages=[{"role": "system", "content": system_prompt},
                  {"role": "user", "content": f"聊天记录:\n{chat_text}"}],
        tools=tools,
        execute=lambda name, args: registry[name](**args),
    )
    # 模型可能漏调工具;按依赖顺序补全缺失步骤,保证结果完整。
    for name in _REQUIRED_ORDER:
        if _STATE_KEY[name] not in state:
            registry[name](chat_text)

    spam = state.get("spam")
    if spam and spam.is_invalid_lead:
        return PipelineResult(status="invalid_lead", spam_check=spam)
    missing = [k for k in ("profile", "compliance", "draft", "spam_risk") if k not in state]
    if missing:
        raise RuntimeError("Agent 未能完成所有分析步骤")
    return PipelineResult(
        status="completed",
        spam_check=spam,
        customer_profile=state["profile"],
        compliance_report=state["compliance"],
        email_draft=state["draft"],
        email_spam_risk=state["spam_risk"],
    )
