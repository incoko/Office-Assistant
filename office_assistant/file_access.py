from __future__ import annotations

from pathlib import Path
import os


class FileAccessError(PermissionError):
    pass


class AuthorizedFileAccess:
    """File boundary for user-selected inputs and approved output directories."""

    def __init__(self, authorized_files: list[str | Path] | None = None, authorized_directories: list[str | Path] | None = None):
        self.files = {self._resolve(path) for path in (authorized_files or [])}
        self.directories = {self._resolve(path) for path in (authorized_directories or [])}

    @staticmethod
    def _resolve(path: str | Path) -> Path:
        return Path(path).expanduser().resolve(strict=False)

    def _is_under(self, path: Path, roots: set[Path]) -> bool:
        return any(path == root or root in path.parents for root in roots)

    def authorize_read(self, path: str | Path) -> Path:
        resolved = self._resolve(path)
        if resolved not in self.files and not self._is_under(resolved, self.directories):
            raise FileAccessError(f"未授权读取：{path}")
        if not resolved.exists() or not resolved.is_file():
            raise FileNotFoundError(path)
        return resolved

    def authorize_output_directory(self, directory: str | Path) -> Path:
        resolved = self._resolve(directory)
        if not self._is_under(resolved, self.directories):
            raise FileAccessError(f"未授权输出目录：{directory}")
        resolved.mkdir(parents=True, exist_ok=True)
        return resolved

    def new_output_path(self, directory: str | Path, filename: str) -> Path:
        if Path(filename).name != filename or filename in {".", ".."}:
            raise FileAccessError("输出文件名不能包含路径")
        target_dir = self.authorize_output_directory(directory)
        stem, suffix = Path(filename).stem, Path(filename).suffix
        candidate = target_dir / filename
        index = 1
        while candidate.exists():
            candidate = target_dir / f"{stem} ({index}){suffix}"
            index += 1
        return candidate

    def write_new_text(self, directory: str | Path, filename: str, content: str, encoding: str = "utf-8") -> Path:
        path = self.new_output_path(directory, filename)
        path.write_text(content, encoding=encoding, newline="")
        return path
