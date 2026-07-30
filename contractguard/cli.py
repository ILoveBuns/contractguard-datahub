from __future__ import annotations

import argparse
import json
from pathlib import Path

from .engine import review_sql
from .fixture_catalog import FixtureCatalog


def main() -> None:
    parser = argparse.ArgumentParser(description="Review SQL changes against DataHub metadata.")
    parser.add_argument("sql", help="SQL file to review")
    parser.add_argument("--catalog", default="fixtures/catalog.json")
    parser.add_argument("--write-back", action="store_true")
    parser.add_argument("--output")
    args = parser.parse_args()
    catalog = FixtureCatalog(args.catalog)
    result = review_sql(Path(args.sql).read_text(), catalog, args.write_back)
    rendered = json.dumps(result.to_dict(), indent=2)
    if args.output:
        Path(args.output).write_text(rendered + "\n")
    print(rendered)


if __name__ == "__main__":
    main()

