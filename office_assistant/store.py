from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, TypeVar

from .models import AgentProfile, ModelConnection, McpServerConfig, SkillPackage, Task, TaskStatus
from .paths import ensure_user_dirs

T = TypeVar("T")


class JsonStore:
    """Small versioned local store. Secrets are referenced, never stored here."""

    FORMAT_VERSION = 1

    def __init__(self, root: Path | None = None):
        self.dirs = ensure_user_dirs(root)
        self.path = self.dirs["config"] / "state.json"
        self.state: dict[str, Any] = self._load()

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"format_version": self.FORMAT_VERSION, "models": [], "agents": [], "skills": [], "mcp_servers": [], "tasks": []}
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            if raw.get("format_version") != self.FORMAT_VERSION:
                raise ValueError("unsupported local state format")
            return raw
        except (OSError, ValueError, json.JSONDecodeError):
            return {"format_version": self.FORMAT_VERSION, "models": [], "agents": [], "skills": [], "mcp_servers": [], "tasks": []}

    def save(self) -> None:
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.state, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.path)

    def _put(self, key: str, value: Any) -> None:
        encoded = asdict(value)
        if isinstance(value, Task):
            encoded["status"] = value.status.value
        items = self.state.setdefault(key, [])
        for index, old in enumerate(items):
            if old.get("id") == encoded.get("id"):
                items[index] = encoded
                break
        else:
            items.append(encoded)
        self.save()

    def save_model(self, value: ModelConnection) -> None: self._put("models", value)
    def save_agent(self, value: AgentProfile) -> None: self._put("agents", value)
    def save_skill(self, value: SkillPackage) -> None: self._put("skills", value)
    def save_mcp(self, value: McpServerConfig) -> None: self._put("mcp_servers", value)
    def save_task(self, value: Task) -> None: self._put("tasks", value)

    def models(self) -> list[ModelConnection]:
        return [ModelConnection(**x) for x in self.state.get("models", [])]

    def agents(self) -> list[AgentProfile]:
        return [AgentProfile(**x) for x in self.state.get("agents", [])]

    def skills(self) -> list[SkillPackage]:
        return [SkillPackage(**x) for x in self.state.get("skills", [])]

    def mcp_servers(self) -> list[McpServerConfig]:
        return [McpServerConfig(**x) for x in self.state.get("mcp_servers", [])]

    def tasks(self) -> list[Task]:
        result = []
        for x in self.state.get("tasks", []):
            copy = dict(x)
            copy["status"] = TaskStatus(copy.get("status", TaskStatus.FAILED.value))
            result.append(Task(**copy))
        return result
