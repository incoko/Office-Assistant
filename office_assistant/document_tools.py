from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET


def read_docx_text(path: str | Path) -> str:
    with ZipFile(path) as archive:
        xml = archive.read("word/document.xml")
    root = ET.fromstring(xml)
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    paragraphs = []
    for paragraph in root.findall(".//w:p", ns):
        text = "".join(node.text or "" for node in paragraph.findall(".//w:t", ns))
        if text:
            paragraphs.append(text)
    return "\n".join(paragraphs)


def read_text_document(path: str | Path) -> str:
    suffix = Path(path).suffix.lower()
    if suffix == ".docx":
        return read_docx_text(path)
    if suffix in {".txt", ".md"}:
        return Path(path).read_text(encoding="utf-8")
    raise ValueError(f"第一版暂不支持文档格式: {suffix}")
