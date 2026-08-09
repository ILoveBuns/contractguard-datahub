import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from contractguard.cli import main


class CLITest(unittest.TestCase):
    def test_live_read_only_uses_official_mcp_adapter(self):
        client = MagicMock()
        manager = MagicMock()
        manager.__enter__.return_value = client
        manager.__exit__.return_value = False
        with tempfile.TemporaryDirectory() as directory:
            sql = Path(directory) / "change.sql"
            sql.write_text("SELECT customer_id FROM analytics.customers;\n")
            with patch("contractguard.cli.MCPClient", return_value=manager) as factory:
                with patch("contractguard.cli.review_sql") as review:
                    review.return_value.to_dict.return_value = {"verdict": "PASS"}
                    main([str(sql), "--live-datahub"])
        factory.assert_called_once_with(enable_mutations=False)
        self.assertFalse(review.call_args.args[2])

    def test_live_writeback_requires_explicit_mutation_opt_in(self):
        with self.assertRaises(SystemExit):
            main(["change.sql", "--live-datahub", "--write-back"])

    def test_mutation_flag_is_rejected_for_fixture_mode(self):
        with self.assertRaises(SystemExit):
            main(["change.sql", "--enable-mutations"])


if __name__ == "__main__":
    unittest.main()
