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
        self.assertIn("ACTIVE_QUERY_USAGE", [x.code for x in result.findings])
        self.assertIn("DataHub usage queries inspected: 2", result.decision_markdown)

    def test_writes_decision_document(self):
        result = review_sql("SELECT customer_id FROM analytics.customers", self.catalog, True)
        self.assertEqual("fixture-document-1", result.writeback_id)
        self.assertEqual(1, len(self.catalog.saved))

    def test_passes_safe_projection(self):
        result = review_sql("SELECT customer_id FROM analytics.customers", self.catalog)
        self.assertEqual("PASS", result.verdict)
        self.assertEqual(0, result.score)

    def test_reviews_select_star(self):
        result = review_sql("SELECT * FROM analytics.customers", self.catalog)
        self.assertEqual("REVIEW", result.verdict)
        self.assertIn("UNSTABLE_PROJECTION", [x.code for x in result.findings])

    def test_blocks_unresolved_asset(self):
        result = review_sql("SELECT id FROM analytics.missing", self.catalog)
        self.assertEqual("REVIEW", result.verdict)
        self.assertIn("UNRESOLVED_ASSET", [x.code for x in result.findings])

    def test_deduplicates_repeated_table_references(self):
        result = review_sql(
            "SELECT * FROM analytics.customers JOIN analytics.customers USING (customer_id)",
            self.catalog,
        )
        self.assertEqual(1, len(result.assets))

    def test_ignores_risk_keywords_in_comments_and_string_literals(self):
        result = review_sql(
            """
            -- ALTER TABLE analytics.customers DROP COLUMN email;
            /* SELECT * FROM analytics.missing; */
            SELECT customer_id, 'DROP COLUMN email FROM analytics.missing'
            FROM analytics.customers;
            """,
            self.catalog,
        )
        self.assertEqual("PASS", result.verdict)
        self.assertEqual(
            ["urn:li:dataset:(urn:li:dataPlatform:snowflake,analytics.customers,PROD)"],
            result.assets,
        )
        self.assertEqual([], result.findings)

    def test_rewrites_only_executable_select_star(self):
        result = review_sql(
            "-- SELECT * FROM analytics.missing\nSELECT * FROM analytics.customers",
            self.catalog,
        )
        self.assertTrue(result.safer_sql.startswith("-- SELECT * FROM analytics.missing"))
        self.assertIn(
            "SELECT /* enumerate approved fields */ FROM analytics.customers",
            result.safer_sql,
        )


if __name__ == "__main__":
    unittest.main()
