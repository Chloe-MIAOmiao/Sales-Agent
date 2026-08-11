from core.agent import run_agent
from core.llm_client import LLMClient
from core.schemas import PipelineResult


def run_pipeline(llm: LLMClient, chat_text: str) -> PipelineResult:
    """通过 ReAct Agent 完成分析:无效线索 → 画像 → 合规审计 → 邮件生成 → 复查。"""
    return run_agent(llm, chat_text)
