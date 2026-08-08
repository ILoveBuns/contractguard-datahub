import os
import unittest
from unittest.mock import MagicMock, patch

from contractguard.mcp_catalog import DataHubMCPCatalog, MCPClient


class FakeClient:
    def __init__(self):
        self.calls = []

    def call(self, name, arguments):
        self.calls.append((name, arguments))
        if name == "search":
            return {"searchResults": [{"entity": {"urn": "urn:customer", "name": "customers"}}]}
        if name == "get_entities":
            return {"entities": [{"urn": "urn:customer", "deprecated": False}]}
        if name == "get_lineage":
            return {"searchResults": [{"entity": {"urn": "urn:dashboard"}}]}
        if name == "get_dataset_queries":
            return {"queries": [{"urn": "urn:query", "properties": {}}]}
        return {"urn": "urn:li:document:decision"}


class MCPCatalogTest(unittest.TestCase):
    def client_process(self):
        process = MagicMock()
        process.stdin = MagicMock()
        process.stdout = iter(
            [
                '{"jsonrpc":"2.0","id":1,"result":{"protocolVersion":"2025-03-26"}}\n'
            ]
        )
        return process

    @patch("contractguard.mcp_catalog.subprocess.Popen")
    def test_mcp_client_disables_mutations_by_default(self, popen):
        popen.return_value = self.client_process()
        with patch.dict(os.environ, {"TOOLS_IS_MUTATION_ENABLED": "true"}):
            MCPClient(["fake-server"])
        self.assertEqual("false", popen.call_args.kwargs["env"]["TOOLS_IS_MUTATION_ENABLED"])

    @patch("contractguard.mcp_catalog.subprocess.Popen")
    def test_mcp_client_requires_explicit_mutation_opt_in(self, popen):
        popen.return_value = self.client_process()
        MCPClient(["fake-server"], enable_mutations=True)
        self.assertEqual("true", popen.call_args.kwargs["env"]["TOOLS_IS_MUTATION_ENABLED"])

    def test_maps_official_tool_flow(self):
        client = FakeClient()
        catalog = DataHubMCPCatalog(client)
        self.assertEqual("urn:customer", catalog.search("customers")[0]["urn"])
        self.assertFalse(catalog.entity("urn:customer")["deprecated"])
        lineage = catalog.lineage("urn:customer")[0]
        self.assertEqual("downstream", lineage["direction"])
        self.assertEqual("urn:dashboard", lineage["urn"])
        self.assertEqual("urn:query", catalog.queries("urn:customer", "email")[0]["urn"])
        self.assertEqual(
            "urn:li:document:decision",
            catalog.save_decision("Decision", "Body", ["urn:customer"]),
        )
        self.assertEqual(
            ["search", "get_entities", "get_lineage", "get_dataset_queries", "save_document"],
            [x[0] for x in client.calls],
        )


if __name__ == "__main__":
    unittest.main()
