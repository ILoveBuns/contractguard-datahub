from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class FixtureCatalog:
    """Deterministic demo adapter with the same semantics as DataHub MCP tools."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.data = json.loads(self.path.read_text())
        self.saved: list[dict[str, Any]] = []

    def search(self, query: str) -> list[dict[str, Any]]:
        q = query.lower().split(".")[-1]
        return [
            {"urn": urn, "name": item["name"]}
            for urn, item in self.data["entities"].items()
            if q in item["name"].lower()
        ]

    def entity(self, urn: str) -> dict[str, Any]:
        return self.data["entities"][urn]

    def lineage(self, urn: str) -> list[dict[str, Any]]:
        return self.data["lineage"].get(urn, [])

    def queries(self, urn: str, column: str | None = None) -> list[dict[str, Any]]:
        queries = self.data.get("queries", {}).get(urn, [])
        if column is None:
            return queries
        needle = column.lower()
        return [
            query for query in queries
            if needle in str(query.get("statement", "")).lower()
        ]

    def save_decision(self, title: str, body: str, urns: list[str]) -> str:
        doc_id = f"fixture-document-{len(self.saved) + 1}"
        self.saved.append({"id": doc_id, "title": title, "body": body, "urns": urns})
        return doc_id
