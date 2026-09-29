from __future__ import annotations

from pathlib import Path
import hashlib
import re

from .document_tools import read_text_document
from .policy_tools import LocalPolicyIndex
from .spreadsheet_tools import read_workbook, raw_totals, validate_rows


def draft_document(input_path: str, kind: str = "周报") -> str:
    text = read_text_document(input_path)
    lines = [line.strip() for line in text.splitlines() if line.strip() and not line.startswith("【")]
    facts = [line for line in lines if any(key in line for key in ("完成", "走访", "更新", "收齐", "提交", "报名"))]
    pending = [line for line in lines if any(key in line for key in ("待定", "尚未", "未", "需要", "负责人"))]
    title = "工作周报草稿" if kind == "周报" else "会议纪要草稿"
    pending_lines = [f"- {line}" for line in pending] or ["- 材料未提供"]
    return "\n".join([title, "（待人工复核；仅根据提供材料整理，不编造缺失信息）", "", "一、已知事项", *[f"- {line}" for line in facts], "", "二、待确认信息", *pending_lines, "", "三、生成约束", "- 生成结果为草稿，不自动发送或提交。"])


def check_spreadsheets(paths: list[str]) -> dict:
    if not paths:
        raise ValueError("请先选择要检查的 Excel 文件。")
    rows = []
    for path in paths:
        rows.extend(read_workbook(path))
    issues = validate_rows(rows)
    return {"rows": rows, "issues": issues, "raw_totals": raw_totals(rows), "valid": bool(rows) and not issues}


def fingerprint(path: str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def query_policy(paths: list[str], query: str) -> list[dict[str, str]]:
    index = LocalPolicyIndex()
    for path in paths:
        index.add(path, fingerprint(path))
    results = []
    for source, excerpt in index.search(query):
        results.append({"source": source.path, "fingerprint": source.fingerprint, "excerpt": excerpt})
    return results
