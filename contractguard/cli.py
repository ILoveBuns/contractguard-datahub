from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from .engine import review_sql
from .fixture_catalog import FixtureCatalog
from .mcp_catalog import DataHubMCPCatalog, MCPClient


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Review SQL changes against DataHub metadata.")
    parser.add_argument("sql", help="SQL file to review")
    parser.add_argument("--catalog", default="fixtures/catalog.json")
    parser.add_argument(
        "--live-datahub",
        action="store_true",
        help="Use the configured official DataHub MCP server instead of the fixture catalog",
    )
    parser.add_argument("--write-back", action="store_true")
    parser.add_argument(
        "--enable-mutations",
        action="store_true",
        help="Allow the live MCP server's mutation tools; required for live --write-back",
    )
    parser.add_argument("--output")
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.enable_mutations and not args.live_datahub:
        parser.error("--enable-mutations requires --live-datahub")
    if args.live_datahub and args.write_back and not args.enable_mutations:
        parser.error("live --write-back requires explicit --enable-mutations")

    sql = Path(args.sql).read_text()
    if args.live_datahub:
        with MCPClient(enable_mutations=args.enable_mutations) as client:
            result = review_sql(sql, DataHubMCPCatalog(client), args.write_back)
    else:
        result = review_sql(sql, FixtureCatalog(args.catalog), args.write_back)
    rendered = json.dumps(result.to_dict(), indent=2)
    if args.output:
        Path(args.output).write_text(rendered + "\n")
    print(rendered)


if __name__ == "__main__":
    main()
