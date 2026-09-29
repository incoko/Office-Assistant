from __future__ import annotations

import json
import urllib.error
import urllib.request
import urllib.parse
import uuid
from dataclasses import dataclass
from typing import Any

from . import __version__
from .security import NetworkPolicy


@dataclass
class McpTool:
    name: str
    description: str
    input_schema: dict[str, Any]

    def model_definition(self) -> dict[str, Any]:
        return {"type": "function", "function": {"name": self.name, "description": self.description, "parameters": self.input_schema}}


class MockMcpClient:
    def __init__(self, tools: list[McpTool] | None = None):
        self.tools = tools or [McpTool("demo_lookup", "返回虚构演示数据", {"type": "object", "properties": {"key": {"type": "string"}}, "required": ["key"]})]
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def list_tools(self) -> list[McpTool]:
        return list(self.tools)

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if not any(tool.name == name for tool in self.tools):
            raise KeyError(f"unknown MCP tool: {name}")
        self.calls.append((name, arguments))
        return {"content": [{"type": "text", "text": f"模拟工具 {name} 返回：{arguments}"}]}


class SseMcpClient:
    """Minimal legacy HTTP+SSE client for deployment validation.

    It performs endpoint policy checks and JSON-RPC POSTs. The exact server-side
    initialization/auth behavior is intentionally validated in the target network.
    """

    def __init__(self, sse_url: str, policy: NetworkPolicy, timeout: int = 30):
        self.sse_url = sse_url
        self.policy = policy
        self.timeout = timeout
        self.message_url: str | None = None
        self.session_id: str | None = None

    def _check(self, url: str) -> None:
        allowed, reason = self.policy.check_url(url)
        if not allowed:
            raise PermissionError(reason)

    def discover_message_endpoint(self) -> str:
        self._check(self.sse_url)
        request = urllib.request.Request(self.sse_url, headers={"Accept": "text/event-stream"})
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                event = None
                data = None
                while True:
                    line = response.readline().decode("utf-8", errors="replace")
                    if not line:
                        break
                    line = line.rstrip("\r\n")
                    if line.startswith("event:"):
                        event = line.split(":", 1)[1].strip()
                    elif line.startswith("data:"):
                        data = line.split(":", 1)[1].strip()
                    elif not line and event == "endpoint" and data:
                        break
                if not data:
                    raise ConnectionError("SSE server did not advertise a message endpoint")
                self.message_url = urllib.parse.urljoin(self.sse_url, data)
                self._check(self.message_url)
                return self.message_url
        except urllib.error.URLError as exc:
            raise ConnectionError(f"MCP SSE connection failed: {exc.reason}") from exc

    def _rpc(self, method: str, params: dict[str, Any] | None = None) -> Any:
        if not self.message_url:
            self.discover_message_endpoint()
        request_id = str(uuid.uuid4())
        payload = {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params or {}}
        self._check(self.message_url or "")
        request = urllib.request.Request(self.message_url or "", data=json.dumps(payload).encode(), headers={"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                value = json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise ConnectionError(f"MCP request failed: {exc.reason}") from exc
        if "error" in value:
            raise RuntimeError(value["error"])
        return value.get("result")

    def initialize(self) -> Any:
        return self._rpc("initialize", {"protocolVersion": "2025-03-26", "capabilities": {}, "clientInfo": {"name": "office-assistant", "version": __version__}})

    def list_tools(self) -> list[McpTool]:
        result = self._rpc("tools/list", {}) or {}
        return [McpTool(x["name"], x.get("description", ""), x.get("inputSchema", {"type": "object"})) for x in result.get("tools", [])]

    def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        return self._rpc("tools/call", {"name": name, "arguments": arguments})
