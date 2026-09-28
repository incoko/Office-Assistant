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
    return rows


def validate_rows(rows: list[Row]) -> list[dict[str, str]]:
    issues = []
    seen: dict[str, list[Row]] = {}
    for row in rows:
        number = row.values.get("事项编号", "")
        seen.setdefault(number, []).append(row)
        for header in HEADERS:
            if not row.values.get(header, "").strip():
                issues.append({"type": "required", "message": f"缺少必填字段：{header}", "source": f"{row.source_file}/{row.source_sheet}/{row.source_row}"})
        deadline = row.values.get("截止日期", "")
        try:
            date.fromisoformat(deadline)
        except ValueError:
            issues.append({"type": "date", "message": f"截止日期不是合法 YYYY-MM-DD：{deadline}", "source": f"{row.source_file}/{row.source_sheet}/{row.source_row}"})
        try:
            expected, done, undone = [int(row.values.get(x, "")) for x in ("应完成人数", "已完成人数", "未完成人数")]
            if min(expected, done, undone) < 0:
                raise ValueError
            if expected != done + undone:
                issues.append({"type": "sum", "message": f"人数不平：{expected} != {done}+{undone}", "source": f"{row.source_file}/{row.source_sheet}/{row.source_row}"})
            if row.values.get("状态") == "已完成" and (done != expected or undone != 0):
                issues.append({"type": "status", "message": "已完成状态与人数不一致", "source": f"{row.source_file}/{row.source_sheet}/{row.source_row}"})
        except ValueError:
            issues.append({"type": "number", "message": "人数必须是非负整数", "source": f"{row.source_file}/{row.source_sheet}/{row.source_row}"})
    for number, matches in seen.items():
        if number and len(matches) > 1:
            issues.append({"type": "duplicate", "message": f"事项编号重复：{number}", "source": "; ".join(f"{r.source_file}/{r.source_row}" for r in matches)})
    return issues


def raw_totals(rows: list[Row]) -> dict[str, int]:
    return {label: sum(int(row.values[label]) for row in rows if row.values.get(label, "").isdigit()) for label in ("应完成人数", "已完成人数", "未完成人数")}
