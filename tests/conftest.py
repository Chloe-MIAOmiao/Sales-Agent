import pytest

from core.llm_client import LLMClient


class FakeLLMClient(LLMClient):
    """返回预设结构化结果的假客户端,不发起真实网络请求。"""

    def __init__(self):
        self.responses: dict[type, object] = {}
        self.calls: list[dict] = []

    def complete_structured(
        self, messages, response_model, temperature=0.1, max_retries=2
    ):
        self.calls.append({"messages": messages, "model": response_model})
        if response_model not in self.responses:
            raise AssertionError(f"未为 {response_model.__name__} 预设响应")
        value = self.responses[response_model]
        if isinstance(value, response_model):
            return value
        return response_model.model_validate(value)

    def expect(self, response_model, value):
        self.responses[response_model] = value
        return self


@pytest.fixture
def fake_llm():
    return FakeLLMClient()
