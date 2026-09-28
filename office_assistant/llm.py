from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Iterator

from .security import NetworkPolicy


@dataclass
class ToolCall:
    name: str
    arguments: dict[str, Any]
    call_id: str = "call-1"


@dataclass
class ChatResult:
    content: str
    tool_calls: list[ToolCall]
    raw: dict[str, Any]


class OpenAICompatibleClient:
    """vLLM-compatible client. Real endpoint testing is deferred to deployment."""

    def __init__(self, base_url: str, model: str, timeout: int = 60, policy: NetworkPolicy | None = None):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.policy = policy or NetworkPolicy()

    def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        endpoint = self.base_url if self.base_url.endswith("/chat/completions") else f"{self.base_url}/chat/completions"
        allowed, reason = self.policy.check_url(endpoint)
        if not allowed:
            raise PermissionError(reason)
        request = urllib.request.Request(endpoint, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise ConnectionError(f"model request failed: {exc.reason}") from exc

    def chat(self, messages: list[dict[str, str]], tools: list[dict[str, Any]] | None = None, tool_choice: str = "auto") -> ChatResult:
        payload: dict[str, Any] = {"model": self.model, "messages": messages, "stream": False}
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = tool_choice
        raw = self._post(payload)
        message = (raw.get("choices") or [{}])[0].get("message") or {}
        calls = []
        for call in message.get("tool_calls") or []:
            function = call.get("function") or {}
            try:
                args = json.loads(function.get("arguments") or "{}")
            except json.JSONDecodeError:
                args = {}
            calls.append(ToolCall(function.get("name", ""), args, call.get("id", "call-1")))
        return ChatResult(message.get("content") or "", calls, raw)


class MockModelClient:
    """Deterministic model used by local tests and disconnected development."""

    def __init__(self, response: str = "模拟模型已收到请求。", requested_tool: ToolCall | None = None, sequence: list[ChatResult] | None = None):
        self.response = response
        self.requested_tool = requested_tool
        self.sequence = list(sequence or [])
        self.calls: list[dict[str, Any]] = []

    def chat(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None = None, tool_choice: str = "auto") -> ChatResult:
        self.calls.append({"messages": messages, "tools": tools, "tool_choice": tool_choice})
        if self.sequence:
            return self.sequence.pop(0)
        return ChatResult(self.response, [self.requested_tool] if self.requested_tool else [], {"mock": True})

    def stream(self, text: str | None = None) -> Iterator[str]:
        value = text or self.response
        for token in value.split():
            yield token + " "
