from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .store import JsonStore


class ConfigPackageError(ValueError):
    pass


class ConfigPackage:
    VERSION = 1

    @classmethod
    def export(cls, store: JsonStore, path: str | Path) -> Path:
        payload = {
            "format_version": cls.VERSION,
            "models": [x for x in store.state.get("models", [])],
            "agents": [x for x in store.state.get("agents", [])],
            "skills": [x for x in store.state.get("skills", [])],
            "mcp_servers": [x for x in store.state.get("mcp_servers", [])],
            "notes": "不包含密钥、任务内容、文档正文、本机目录授权或网络策略。导入后需在本机确认。",
        }
        target = Path(path)
        target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return target

    @classmethod
    def validate(cls, payload: dict[str, Any]) -> None:
        if payload.get("format_version") != cls.VERSION:
            raise ConfigPackageError("不支持的配置包版本")
        for key in ("models", "agents", "skills", "mcp_servers"):
            if not isinstance(payload.get(key, []), list):
                raise ConfigPackageError(f"配置字段格式错误：{key}")
        serialized = json.dumps(payload, ensure_ascii=False).lower()
        for forbidden in ("api_key", "authorization", "password", "secret"):
            if forbidden in serialized:
                raise ConfigPackageError("配置包疑似包含密钥字段")

    @classmethod
    def import_file(cls, store: JsonStore, path: str | Path, apply: bool = False) -> dict[str, Any]:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        cls.validate(payload)
        if apply:
            for key in ("models", "agents", "skills", "mcp_servers"):
                store.state[key] = payload.get(key, [])
            store.save()
        return payload
