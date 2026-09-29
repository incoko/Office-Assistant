from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .credentials import CredentialStore
from .llm import ChatResult, OpenAICompatibleClient
from .models import ModelConnection
from .security import NetworkPolicy
from .store import JsonStore


@dataclass(frozen=True)
class ConnectionCheck:
    ok: bool
    message: str
    models: tuple[str, ...] = ()


class ModelService:
    """Build clients from local config and keep credentials out of JSON state."""

    def __init__(self, store: JsonStore):
        self.store = store
        self.credentials = CredentialStore(store.dirs["base"])

    def save_connection(self, connection: ModelConnection, api_key: str | None = None) -> ModelConnection:
        if api_key:
            connection.credential_ref = self.credentials.put(api_key, connection.credential_ref)
        self.store.save_model(connection)
        return connection

    def client(self, connection: ModelConnection) -> OpenAICompatibleClient:
        # Prototype policy: the explicitly configured model URL is the only target
        # for this client. Deployment-level allowlists will replace this later.
        policy = NetworkPolicy.from_urls([connection.base_url])
        return OpenAICompatibleClient(
            connection.base_url, connection.model, connection.timeout_seconds,
            policy=policy, api_key=self.credentials.get(connection.credential_ref),
        )

    def check(self, connection: ModelConnection, api_key: str | None = None) -> ConnectionCheck:
        if api_key:
            connection = self.save_connection(connection, api_key)
        try:
            models = self.client(connection).list_models()
            available = tuple(str(x.get("id", "")) for x in models if x.get("id"))
            if available and connection.model not in available:
                return ConnectionCheck(False, f"服务已连接，但未找到模型“{connection.model}”。可用模型：{', '.join(available)}", available)
            return ConnectionCheck(True, f"连接成功：{connection.base_url}；模型：{connection.model}", available)
        except Exception as exc:
            return ConnectionCheck(False, f"连接失败：{exc}")

    def chat(self, connection: ModelConnection, messages: list[dict[str, Any]]) -> ChatResult:
        return self.client(connection).chat(messages)

    def by_id(self, connection_id: str | None) -> ModelConnection | None:
        return next((x for x in self.store.models() if x.id == connection_id), None)
