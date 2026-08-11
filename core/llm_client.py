import json
import os

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel

load_dotenv()

DEFAULT_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEFAULT_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEFAULT_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")


class LLMClient:
    """DeepSeek 统一封装:密钥从环境变量读取,结构化 JSON 输出用 Pydantic 校验并重试。"""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
    ):
        if api_key is None:
            api_key = DEFAULT_API_KEY
        if api_key is None:
            raise ValueError(
                "未配置 DEEPSEEK_API_KEY,请在项目根目录 .env 中设置后重试"
            )
        self.client = OpenAI(
            api_key=api_key, base_url=base_url or DEFAULT_BASE_URL
        )
        self.model = model or DEFAULT_MODEL

    def complete_structured(
        self,
        messages: list[dict],
        response_model: type[BaseModel],
        temperature: float = 0.1,
        max_retries: int = 2,
    ) -> BaseModel:
        """要求模型返回符合 response_model 的 JSON,校验失败自动重试。"""
        schema = response_model.model_json_schema()
        system_prompt = (
            "你是一个严格的结构化输出助手。必须只返回符合以下 JSON Schema 的合法 JSON,"
            f"不要包含任何多余文字或 markdown 代码块:\n{json.dumps(schema, ensure_ascii=False)}"
        )
        working_messages = [
            {"role": "system", "content": system_prompt},
            *messages,
        ]

        for attempt in range(max_retries + 1):
            response = self.client.chat.completions.create(
                model=self.model,
                messages=working_messages,
                temperature=temperature,
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content or "{}"
            try:
                data = json.loads(content)
                return response_model.model_validate(data)
            except Exception as e:
                if attempt >= max_retries:
                    raise
                working_messages.append(
                    {
                        "role": "user",
                        "content": (
                            f"你上次的输出无法通过校验: {e}。"
                            "请重新输出一个完全符合 JSON Schema 的合法 JSON。"
                        ),
                    }
                )
        raise RuntimeError("unreachable")

    def complete_tool_loop(
        self,
        messages: list[dict],
        tools: list[dict],
        execute,
        max_steps: int = 8,
        temperature: float = 0.3,
    ) -> dict:
        """ReAct 工具循环:模型请求工具则执行并回传,直到模型输出最终答案。"""
        working = [*messages]
        for step in range(max_steps):
            response = self.client.chat.completions.create(
                model=self.model,
                messages=working,
                tools=tools,
                temperature=temperature,
            )
            message = response.choices[0].message
            if message.tool_calls:
                working.append(message)
                for tc in message.tool_calls:
                    name = tc.function.name
                    try:
                        args = json.loads(tc.function.arguments or "{}")
                    except json.JSONDecodeError:
                        args = {}
                    try:
                        obs = str(execute(name, args))
                    except Exception as e:
                        obs = f"ERROR: {e}"
                    working.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": obs,
                        }
                    )
                continue
            return {"final": message.content or "", "steps": step + 1}
        return {"final": "", "steps": max_steps, "timeout": True}
