from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET
import re

NS = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main", "rel": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}
HEADERS = ["事项编号", "网点", "事项名称", "负责人", "截止日期", "状态", "应完成人数", "已完成人数", "未完成人数"]

@dataclass
class Row:
    source_file: str
    source_sheet: str
    source_row: int
    values: dict[str, str]


def _col_name(number: int) -> str:
    result = ""
    while number:
        number, rem = divmod(number - 1, 26)
        result = chr(65 + rem) + result
    return result


def read_workbook(path: str | Path) -> list[Row]:
    path = Path(path)
    with ZipFile(path) as archive:
        shared = []
        if "xl/sharedStrings.xml" in archive.namelist():
            root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            shared = ["".join(x.text or "" for x in si.findall(".//{*}t")) for si in root.findall("{*}si")]
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        rel_map = {r.attrib["Id"]: r.attrib["Target"] for r in rels}
        rows: list[Row] = []
        for sheet in workbook.findall(".//{*}sheet"):
            if sheet.attrib["name"] != "事项台账":
                continue
            target = rel_map[sheet.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"]]
            xml_name = "xl/" + target if not target.startswith("xl/") else target
            root = ET.fromstring(archive.read(xml_name))
            parsed = []
            for row in root.findall(".//{*}row"):
                values = {}
                for cell in row.findall("{*}c"):
                    ref = cell.attrib.get("r", "")
                    col = re.match(r"([A-Z]+)", ref)
                    if not col:
                        continue
                    value = cell.find("{*}v")
                    text = value.text if value is not None else ""
                    if cell.attrib.get("t") == "s" and text:
                        text = shared[int(text)]
                    inline = cell.find(".//{*}t")
                    if inline is not None:
                        text = inline.text or ""
                    values[col.group(1)] = text
                parsed.append((int(row.attrib.get("r", "0")), values))
            if not parsed:
                continue
            header = {value: key for key, value in parsed[0][1].items()}
            if list(header)[:len(HEADERS)] != HEADERS:
                raise ValueError(f"{path.name}: 事项台账表头不符合 DEMO-TASK-1.0")
            for row_number, values in parsed[1:]:
                if not any(values.values()):
                    continue
                rows.append(Row(path.name, "事项台账", row_number, {h: values.get(col, "") for h, col in header.items()}))
            return rows
    raise ValueError(f"{path.name}: 未找到有效的“事项台账”工作表")


NUMBER_FIELDS = ("应完成人数", "已完成人数", "未完成人数")


def _location(row: Row, fields: tuple[str, ...]) -> dict:
    return {"file": row.source_file, "sheet": row.source_sheet, "row": row.source_row,
            "cells": [f"{_col_name(HEADERS.index(field) + 1)}{row.source_row}" for field in fields]}


def _issue(kind: str, message: str, matches: list[Row], fields: tuple[str, ...]) -> dict:
    return {"type": kind, "message": message,
            "source": "; ".join(f"{r.source_file}/{r.source_sheet}/{r.source_row}" for r in matches),
            "locations": [_location(row, fields) for row in matches]}


def validate_rows(rows: list[Row]) -> list[dict]:
    issues = []
    seen: dict[str, list[Row]] = {}
    for row in rows:
        number = row.values.get("事项编号", "")
        seen.setdefault(number, []).append(row)
        for header in HEADERS:
            if not row.values.get(header, "").strip():
                issues.append(_issue("required", f"缺少必填字段：{header}", [row], (header,)))
        deadline = row.values.get("截止日期", "")
        try:
            if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", deadline):
                raise ValueError
            date.fromisoformat(deadline)
        except ValueError:
            issues.append(_issue("date", f"截止日期不是合法 YYYY-MM-DD：{deadline}", [row], ("截止日期",)))
        state = row.values.get("状态", "")
        if state and state not in {"未开始", "进行中", "已完成"}:
            issues.append(_issue("status", f"状态不在允许范围内：{state}", [row], ("状态",)))
        try:
            expected, done, undone = [int(row.values.get(x, "")) for x in NUMBER_FIELDS]
            if min(expected, done, undone) < 0:
                raise ValueError
            if expected != done + undone:
                issues.append(_issue("sum", f"人数不平：{expected} != {done}+{undone}", [row], NUMBER_FIELDS))
            if state == "已完成" and (done != expected or undone != 0):
                issues.append(_issue("status", "已完成状态与人数不一致", [row], ("状态",) + NUMBER_FIELDS))
        except ValueError:
            issues.append(_issue("number", "人数必须是非负整数", [row], NUMBER_FIELDS))
    for number, matches in seen.items():
        if number and len(matches) > 1:
            issues.append(_issue("duplicate", f"事项编号重复：{number}", matches, ("事项编号",)))
    return issues


def raw_totals(rows: list[Row]) -> dict[str, int | None]:
    # Never silently omit malformed values and present a partial sum as a total.
    totals = {}
    for label in NUMBER_FIELDS:
        try:
            values = [int(row.values.get(label, "")) for row in rows]
            totals[label] = sum(values) if all(value >= 0 for value in values) else None
        except ValueError:
            totals[label] = None
    return totals
