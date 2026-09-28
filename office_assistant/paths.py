from __future__ import annotations

import os
from pathlib import Path

APP_NAME = "Office Assistant"


def user_data_dir() -> Path:
    """Return a writable per-user directory; installation files stay elsewhere."""
    root = os.environ.get("LOCALAPPDATA") or os.environ.get("XDG_DATA_HOME")
    if root:
        return Path(root) / APP_NAME
    return Path.home() / ".office-assistant"


def ensure_user_dirs(root: Path | None = None) -> dict[str, Path]:
    base = root or user_data_dir()
    dirs = {"base": base, "config": base / "config", "tasks": base / "tasks", "cache": base / "cache", "artifacts": base / "artifacts", "logs": base / "logs"}
    for path in dirs.values():
        path.mkdir(parents=True, exist_ok=True)
    return dirs


def resource_dir() -> Path:
    """PyInstaller onedir keeps read-only resources in sys._MEIPASS."""
    import sys
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
