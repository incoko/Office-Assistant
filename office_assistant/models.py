from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
import uuid


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    WAITING_CONFIRMATION = "waiting_confirmation"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    INTERRUPTED = "interrupted"


@dataclass
class ModelConnection:
    id: str
    name: str
    base_url: str
    model: str
    credential_ref: str | None = None
    timeout_seconds: int = 60
    provider: str = "vllm-openai-compatible"


@dataclass
class SkillPackage:
    id: str
    name: str
    description: str
    root_path: str
    content_fingerprint: str
    enabled: bool = True


@dataclass
class McpServerConfig:
    id: str
    name: str
    transport_type: str
    url: str
    credential_ref: str | None = None
    enabled: bool = False
    discovered_tools: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class AgentProfile:
    id: str
    name: str
    system_prompt: str
    model_connection_id: str | None = None
    skill_ids: list[str] = field(default_factory=list)
    mcp_server_ids: list[str] = field(default_factory=list)
    enabled_tool_names: list[str] = field(default_factory=list)
    working_directories: list[str] = field(default_factory=list)
    enabled: bool = True
    version: int = 1

    def snapshot(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Artifact:
    id: str
    path: str
    kind: str
    created_at: str = field(default_factory=utc_now)


@dataclass
class Task:
    id: str
    agent_id: str
    title: str
    status: TaskStatus = TaskStatus.PENDING
    input_files: list[str] = field(default_factory=list)
    output_files: list[str] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)
    agent_snapshot: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def new(cls, agent: AgentProfile, title: str, input_files: list[str] | None = None) -> "Task":
        return cls(
            id=str(uuid.uuid4()),
            agent_id=agent.id,
            title=title,
            input_files=input_files or [],
            agent_snapshot=agent.snapshot(),
        )

    def event(self, kind: str, message: str, **details: Any) -> None:
        self.events.append({"at": utc_now(), "kind": kind, "message": message, **details})
        self.updated_at = utc_now()
