import unittest

from contractguard.engine import review_sql
from contractguard.fixture_catalog import FixtureCatalog


class EngineTest(unittest.TestCase):
    def setUp(self):
        self.catalog = FixtureCatalog("fixtures/catalog.json")

    def test_blocks_breaking_downstream_change(self):
        result = review_sql(
            "ALTER TABLE analytics.customers DROP COLUMN email; SELECT * FROM analytics.customers;",
            self.catalog,
        )
        self.assertEqual("BLOCK", result.verdict)
        self.assertGreaterEqual(result.score, 50)
        self.assertIn("BREAKING_LINEAGE", [x.code for x in result.findings])

    def test_writes_decision_document(self):
        result = review_sql("SELECT customer_id FROM analytics.customers", self.catalog, True)
        self.assertEqual("fixture-document-1", result.writeback_id)
        self.assertEqual(1, len(self.catalog.saved))


if __name__ == "__main__":
    unittest.main()

