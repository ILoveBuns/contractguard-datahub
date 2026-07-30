from __future__ import annotations

import json
import os
import subprocess
import threading
from typing import Any


class MCPClient:
    """Small stdio JSON-RPC client for the official DataHub MCP server."""

    def __init__(self, command: list[str] | None = None):
        command = command or os.environ.get(
            "DATAHUB_MCP_COMMAND", "mcp-server-datahub --transport stdio"
        ).split()
        env = os.environ.copy()
        env.setdefault("TOOLS_IS_MUTATION_ENABLED", "true")
        self.process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=None,
            text=True,
            bufsize=1,
            env=env,
        )
        self._id = 0
        self._lock = threading.Lock()
        self._request(
            "initialize",
            {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {"name": "contractguard", "version": "0.1.0"},
            },
        )
        self._notify("notifications/initialized", {})

    def _write(self, payload: dict[str, Any]) -> None:
        assert self.process.stdin
        self.process.stdin.write(json.dumps(payload, separators=(",", ":")) + "\n")
        self.process.stdin.flush()

    def _request(self, method: str, params: dict[str, Any]) -> Any:
        with self._lock:
            self._id += 1
            request_id = self._id
            self._write({"jsonrpc": "2.0", "id": request_id, "method": method, "params": params})
            assert self.process.stdout
            for line in self.process.stdout:
                message = json.loads(line)
                if message.get("id") != request_id:
                    continue
                if "error" in message:
                    raise RuntimeError(f"MCP error: {message['error']}")
                return message.get("result")
        raise RuntimeError("DataHub MCP server closed its output stream")

    def _notify(self, method: str, params: dict[str, Any]) -> None:
        self._write({"jsonrpc": "2.0", "method": method, "params": params})

    def call(self, name: str, arguments: dict[str, Any]) -> Any:
        result = self._request("tools/call", {"name": name, "arguments": arguments})
        if result.get("isError"):
            raise RuntimeError(f"DataHub tool {name} failed: {result}")
        if result.get("structuredContent"):
            return result["structuredContent"]
        texts = [x.get("text", "") for x in result.get("content", []) if x.get("type") == "text"]
        combined = "\n".join(texts)
        try:
            return json.loads(combined)
        except json.JSONDecodeError:
            return {"text": combined}

    def close(self) -> None:
        if self.process.poll() is None:
            self.process.terminate()
            self.process.wait(timeout=5)

    def __enter__(self) -> "MCPClient":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()


def _find_records(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        records = [x for x in value if isinstance(x, dict)]
        return records or sum((_find_records(x) for x in value), [])
    if isinstance(value, dict):
        if "urn" in value:
            return [value]
        for key in ("searchResults", "entities", "results", "items"):
            if key in value:
                found = _find_records(value[key])
                if found:
                    return found
        for child in value.values():
            found = _find_records(child)
            if found:
                return found
    return []


class DataHubMCPCatalog:
    def __init__(self, client: MCPClient):
        self.client = client

    def search(self, query: str) -> list[dict[str, Any]]:
        result = self.client.call("search", {"query": f'/q "{query}"', "num_results": 5})
        records = _find_records(result)
        return [
            {
                **record,
                "urn": record.get("urn") or record.get("entity", {}).get("urn"),
                "name": record.get("name")
                or record.get("entity", {}).get("name")
                or query,
            }
            for record in records
        ]

    def entity(self, urn: str) -> dict[str, Any]:
        result = self.client.call("get_entities", {"urns": urn})
        records = _find_records(result)
        return records[0] if records else (result if isinstance(result, dict) else {})

    def lineage(self, urn: str) -> list[dict[str, Any]]:
        result = self.client.call(
            "get_lineage",
            {"urn": urn, "upstream": False, "max_hops": 3, "max_results": 50},
        )
        return [
            {
                **x,
                "urn": x.get("urn") or x.get("entity", {}).get("urn"),
                "direction": "downstream",
            }
            for x in _find_records(result)
        ]

    def save_decision(self, title: str, body: str, urns: list[str]) -> str:
        result = self.client.call(
            "save_document",
            {
                "document_type": "Decision",
                "title": title,
                "content": body,
                "related_assets": urns,
            },
        )
        if isinstance(result, dict):
            return str(result.get("urn") or result.get("id") or result)
        return str(result)
