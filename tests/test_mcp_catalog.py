import unittest

from contractguard.mcp_catalog import DataHubMCPCatalog


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
        return {"urn": "urn:li:document:decision"}


class MCPCatalogTest(unittest.TestCase):
    def test_maps_official_tool_flow(self):
        client = FakeClient()
        catalog = DataHubMCPCatalog(client)
        self.assertEqual("urn:customer", catalog.search("customers")[0]["urn"])
        self.assertFalse(catalog.entity("urn:customer")["deprecated"])
        lineage = catalog.lineage("urn:customer")[0]
        self.assertEqual("downstream", lineage["direction"])
        self.assertEqual("urn:dashboard", lineage["urn"])
        self.assertEqual(
            "urn:li:document:decision",
            catalog.save_decision("Decision", "Body", ["urn:customer"]),
        )
        self.assertEqual(
            ["search", "get_entities", "get_lineage", "save_document"],
            [x[0] for x in client.calls],
        )


if __name__ == "__main__":
    unittest.main()
