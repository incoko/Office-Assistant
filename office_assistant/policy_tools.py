from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from .document_tools import read_text_document

@dataclass
class Source:
    path: str
    text: str
    fingerprint: str

class LocalPolicyIndex:
    def __init__(self):
        self.sources: dict[str, Source] = {}

    def add(self, path: str | Path, fingerprint: str) -> Source:
        text = read_text_document(path)
        source = Source(str(path), text, fingerprint)
        self.sources[str(path)] = source
        return source

    def remove(self, path: str) -> None:
        self.sources.pop(path, None)

    def search(self, query: str, limit: int = 5) -> list[tuple[Source, str]]:
        terms = [x for x in query.lower().split() if x]
        results = []
        for source in self.sources.values():
            lines = source.text.splitlines()
            for index, line in enumerate(lines):
                if any(term in line.lower() for term in terms):
                    start = max(0, index - 1)
                    end = min(len(lines), index + 2)
                    results.append((source, "\n".join(lines[start:end])))
                    break
        return results[:limit]
