from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Protocol

from .llm import ChatResult
from .mcp import McpTool
from .models import AgentProfile, Task, TaskStatus
from .store import JsonStore


class ModelClient(Protocol):
    def chat(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None = None, tool_choice: str = "auto") -> ChatResult: ...


class ToolClient(Protocol):
    def call_tool(self, name: str, arguments: dict[str, Any]) -> Any: ...


@dataclass
class RegisteredTool:
    definition: McpTool
    client: ToolClient
    enabled: bool = False


def _matches_type(value: Any, expected: str) -> bool:
    return {
        "string": isinstance(value, str),
        "object": isinstance(value, dict),
        "array": isinstance(value, list),
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "number": isinstance(value, (int, float)) and not isinstance(value, bool),
        "boolean": isinstance(value, bool),
    }.get(expected, True)


def validate_tool_arguments(tool: McpTool, arguments: dict[str, Any]) -> None:
    if not isinstance(arguments, dict):
        raise ValueError(f"tool arguments must be an object: {tool.name}")
    schema = tool.input_schema or {}
    for name in schema.get("required", []):
        if name not in arguments:
            raise ValueError(f"missing required argument {name}: {tool.name}")
    for name, value in arguments.items():
        spec = (schema.get("properties") or {}).get(name, {})
        expected = spec.get("type")
        if expected and not _matches_type(value, expected):
            raise ValueError(f"invalid argument type for {tool.name}.{name}: expected {expected}")


class AgentRuntime:
    def __init__(self, store: JsonStore, model: ModelClient, max_rounds: int = 3, max_tool_calls: int = 8, max_result_chars: int = 4000):
        self.store = store
        self.model = model
        self.max_rounds = max_rounds
        self.max_tool_calls = max_tool_calls
        self.max_result_chars = max_result_chars
        self.tools: dict[str, RegisteredTool] = {}
        self.active_task: Task | None = None

    def register_mcp_tools(self, tools: list[McpTool], client: ToolClient) -> None:
        for tool in tools:
            self.tools[tool.name] = RegisteredTool(tool, client, enabled=False)

    def enable_tool(self, name: str, enabled: bool = True) -> None:
        if name not in self.tools:
            raise KeyError(name)
        self.tools[name].enabled = enabled

    def _available_tools(self, agent: AgentProfile, authorized_tool_names: set[str]) -> list[dict[str, Any]]:
        return [
            registered.definition.model_definition()
            for registered in self.tools.values()
            if registered.enabled and registered.definition.name in agent.enabled_tool_names and registered.definition.name in authorized_tool_names
        ]

    def run(self, agent: AgentProfile, title: str, user_text: str, input_files: list[str] | None = None, authorized_tool_names: list[str] | None = None, messages: list[dict[str, Any]] | None = None) -> Task:
        if self.active_task and self.active_task.status in {TaskStatus.RUNNING, TaskStatus.WAITING_CONFIRMATION}:
            raise RuntimeError("another task is already running")
        task = Task.new(agent, title, input_files)
        task.status = TaskStatus.RUNNING
        task.event("task_started", "任务开始")
        self.active_task = task
        authorized = set(authorized_tool_names or [])
        if messages:
            messages = list(messages)
            if not messages or messages[0].get("role") != "system":
                messages.insert(0, {"role": "system", "content": agent.system_prompt})
        else:
            messages = [{"role": "system", "content": agent.system_prompt}, {"role": "user", "content": user_text}]
        try:
            tool_calls_used = 0
            for round_number in range(1, self.max_rounds + 1):
                response = self.model.chat(messages, self._available_tools(agent, authorized) or None, "auto")
                if not response.tool_calls:
                    task.event("assistant_message", response.content)
                    task.status = TaskStatus.SUCCEEDED
                    break
                messages.append({"role": "assistant", "content": response.content, "tool_calls": [call.name for call in response.tool_calls]})
                for call in response.tool_calls:
                    tool_calls_used += 1
                    if tool_calls_used > self.max_tool_calls:
                        raise RuntimeError("tool call limit reached")
                    registered = self.tools.get(call.name)
                    if not registered or not registered.enabled or call.name not in agent.enabled_tool_names or call.name not in authorized:
                        task.event("tool_rejected", "工具未授权", tool=call.name)
                        raise PermissionError(f"tool not authorized: {call.name}")
                    validate_tool_arguments(registered.definition, call.arguments)
                    task.event("tool_call", "调用工具", tool=call.name, round=round_number)
                    result = registered.client.call_tool(call.name, call.arguments)
                    result_text = str(result)[: self.max_result_chars]
                    task.event("tool_result", "工具返回", tool=call.name, result_preview=result_text)
                    messages.append({"role": "tool", "name": call.name, "content": result_text})
            else:
                raise RuntimeError("tool round limit reached")
            if task.status == TaskStatus.RUNNING:
                raise RuntimeError("model did not produce a final response")
        except Exception as exc:
            task.error = str(exc)
            task.event("task_failed", "任务失败", error=str(exc))
            task.status = TaskStatus.FAILED
        finally:
            self.store.save_task(task)
            self.active_task = None
        return task
