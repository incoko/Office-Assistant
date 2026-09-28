from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import hashlib
import re

from .models import SkillPackage
from .store import JsonStore


@dataclass
class SkillImportResult:
    package: SkillPackage
    warnings: list[str]


class SkillImporter:
    """Import local instruction skills without downloading or executing code."""

    def __init__(self, store: JsonStore):
        self.store = store

    @staticmethod
    def _fingerprint(root: Path) -> str:
        digest = hashlib.sha256()
        for path in sorted(p for p in root.rglob("*") if p.is_file()):
            digest.update(path.relative_to(root).as_posix().encode())
            digest.update(path.read_bytes())
        return digest.hexdigest()

    @staticmethod
    def _metadata(text: str, root: Path) -> tuple[str, str]:
        heading = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
        name = heading.group(1).strip() if heading else root.name
        description_match = re.search(r"^description\s*:\s*(.+)$", text, re.MULTILINE | re.IGNORECASE)
        description = description_match.group(1).strip() if description_match else "本地 Skill 指令"
        return name, description

    def import_directory(self, directory: str | Path) -> SkillImportResult:
        root = Path(directory).expanduser().resolve()
        skill_file = root / "SKILL.md"
        if not root.is_dir() or not skill_file.is_file():
            raise ValueError("Skill 目录必须包含可读的 SKILL.md")
        text = skill_file.read_text(encoding="utf-8")
        name, description = self._metadata(text, root)
        warnings: list[str] = []
        for script in root.rglob("*"):
            if script.is_file() and script.suffix.lower() in {".py", ".ps1", ".bat", ".cmd", ".sh", ".exe"}:
                warnings.append(f"发现未启用的可执行文件：{script.relative_to(root)}")
        for reference in re.findall(r"(?:\]\(|\]\s*:\s*)<?([^)>\s]+)", text):
            if reference.startswith(("http://", "https://", "#")):
                continue
            target = (root / reference).resolve()
            if root not in target.parents and target != root:
                raise ValueError(f"Skill 引用越出目录：{reference}")
            if not target.exists():
                warnings.append(f"引用文件不存在：{reference}")
        package = SkillPackage(str(self._fingerprint(root)[:16]), name, description, str(root), self._fingerprint(root))
        self.store.save_skill(package)
        return SkillImportResult(package, warnings)
