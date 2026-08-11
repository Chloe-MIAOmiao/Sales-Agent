import json
import types

from core.llm_client import LLMClient


class FakeCompletions:
    def __init__(self, responses):
        self.responses = list(responses)
        self.i = 0
    def create(self, **kwargs):
        r = self.responses[min(self.i, len(self.responses) - 1)]
        self.i += 1
        return r


class FakeChat:
    def __init__(self, responses):
        self.completions = FakeCompletions(responses)


class FakeOpenAI:
    def __init__(self, responses):
        self.chat = FakeChat(responses)


def _tool_call(name, args, call_id="call_1"):
    fn = types.SimpleNamespace(name=name, arguments=json.dumps(args))
    return types.SimpleNamespace(id=call_id, function=fn)


def _msg_response(tool_calls=None, content=None):
    msg = types.SimpleNamespace(tool_calls=tool_calls, content=content)
    return types.SimpleNamespace(choices=[types.SimpleNamespace(message=msg)])


def test_tool_loop_executes_tools_until_final():
    tool1 = _msg_response(tool_calls=[_tool_call("echo", {"x": 1})])
    final = _msg_response(content='{"ok": true}')
    client = LLMClient.__new__(LLMClient)
    client.model = "deepseek-chat"
    client.client = FakeOpenAI([tool1, final])
    executed = []
    result = client.complete_tool_loop(
        messages=[{"role": "user", "content": "go"}],
        tools=[{"type": "function", "function": {"name": "echo", "parameters": {"type": "object", "properties": {}}}}],
        execute=lambda name, args: executed.append((name, args)) or "done",
    )
    assert executed == [("echo", {"x": 1})]
    assert result["final"] == '{"ok": true}'


def test_tool_loop_caps_steps():
    tool1 = _msg_response(tool_calls=[_tool_call("echo", {})])
    client = LLMClient.__new__(LLMClient)
    client.model = "deepseek-chat"
    client.client = FakeOpenAI([tool1])
    result = client.complete_tool_loop(
        messages=[{"role": "user", "content": "go"}],
        tools=[{"type": "function", "function": {"name": "echo", "parameters": {"type": "object", "properties": {}}}}],
        execute=lambda name, args: "done", max_steps=2,
    )
    assert result["steps"] <= 2
