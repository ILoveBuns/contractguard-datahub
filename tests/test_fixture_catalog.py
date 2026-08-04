import unittest

from contractguard.fixture_catalog import FixtureCatalog


class FixtureCatalogTest(unittest.TestCase):
    def setUp(self):
        self.catalog = FixtureCatalog("fixtures/catalog.json")
        self.urn = next(iter(self.catalog.data["entities"]))

    def test_filters_queries_by_column(self):
        self.assertEqual(2, len(self.catalog.queries(self.urn, "email")))
        self.assertEqual([], self.catalog.queries(self.urn, "country"))

    def test_returns_all_queries_without_column_filter(self):
        self.assertEqual(2, len(self.catalog.queries(self.urn)))

    def test_saved_decisions_are_observable(self):
        document_id = self.catalog.save_decision("Decision", "Body", [self.urn])
        self.assertEqual("fixture-document-1", document_id)
        self.assertEqual([self.urn], self.catalog.saved[0]["urns"])


if __name__ == "__main__":
    unittest.main()
