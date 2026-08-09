from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any, Protocol


class Catalog(Protocol):
    def search(self, query: str) -> list[dict[str, Any]]: ...
    def entity(self, urn: str) -> dict[str, Any]: ...
    def lineage(self, urn: str) -> list[dict[str, Any]]: ...
    def queries(self, urn: str, column: str | None = None) -> list[dict[str, Any]]: ...
    def save_decision(self, title: str, body: str, urns: list[str]) -> str: ...


@dataclass
class Finding:
    severity: str
    code: str
    message: str
    evidence: list[str]


@dataclass
class Review:
    verdict: str
    score: int
    assets: list[str]
    findings: list[Finding]
    safer_sql: str
    decision_markdown: str
    writeback_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


_SELECT_STAR_RE = re.compile(r"\bselect\s+\*", re.I)
# Keep discovery lightweight while handling DROP TABLE IF EXISTS without
# mistaking IF for the asset.
_TABLE_RE = re.compile(
    r"\b(?:from|join|update|into|table)\s+(?:if\s+exists\s+)?([^\s;,]+)",
    re.I,
)
_DROP_COLUMN_RE = re.compile(r"\bdrop\s+column\s+([^\s;,]+)", re.I)
_DROP_TABLE_RE = re.compile(
    r"\bdrop\s+table\s+(?:if\s+exists\s+)?([^\s;,]+)",
    re.I,
)
_NON_CODE_RE = re.compile(
    r"--[^\r\n]*|/\*.*?\*/|'(?:''|[^'])*'",
    re.DOTALL,
)


def _clean(value: str) -> str:
    return value.strip("`\"")


def _executable_sql(sql: str) -> str:
    """Mask comments and string literals while preserving source positions.

    ContractGuard is deliberately not a SQL executor, but risk keywords inside
    prose and literal values must not become schema-change evidence. Replacing
    each non-code span with equal-length whitespace keeps regex boundaries and
    generated diagnostics deterministic without adding a dialect-specific
    parser dependency.
    """

    return _NON_CODE_RE.sub(lambda match: " " * len(match.group(0)), sql)


def review_sql(sql: str, catalog: Catalog, write_back: bool = False) -> Review:
    executable_sql = _executable_sql(sql)
    names = list(dict.fromkeys(_clean(x) for x in _TABLE_RE.findall(executable_sql)))
    assets: list[dict[str, Any]] = []
    for name in names:
        assets.extend(catalog.search(name))

    findings: list[Finding] = []
    urns: list[str] = []
    downstream: list[str] = []
    usage_queries: list[dict[str, Any]] = []
    for asset in assets:
        urn = str(asset.get("urn", ""))
        if not urn or urn in urns:
            continue
        urns.append(urn)
        detail = catalog.entity(urn)
        lineage = catalog.lineage(urn)
        downstream.extend(str(x.get("urn", "")) for x in lineage if x.get("direction") == "downstream")
        if detail.get("deprecated"):
            findings.append(Finding("high", "DEPRECATED_ASSET", f"{asset.get('name', urn)} is deprecated.", [urn]))

    dropped_columns = [_clean(x) for x in _DROP_COLUMN_RE.findall(executable_sql)]
    dropped_tables = [_clean(x) for x in _DROP_TABLE_RE.findall(executable_sql)]
    destructive_change = bool(dropped_columns or dropped_tables)
    for urn in urns:
        # A dropped table invalidates every recorded query for the asset.
        # Column drops can use DataHub's narrower column-aware query lookup.
        query_columns: list[str | None] = (
            [None] if dropped_tables else dropped_columns
        )
        for column in query_columns:
            usage_queries.extend(catalog.queries(urn, column))
    if destructive_change and downstream:
        targets = [
            *(f"column {column}" for column in dropped_columns),
            *(f"table {table}" for table in dropped_tables),
        ]
        findings.append(Finding(
            "critical",
            "BREAKING_LINEAGE",
            f"Dropping {', '.join(targets)} can break {len(set(downstream))} downstream asset(s).",
            sorted(set(downstream)),
        ))
    if destructive_change and usage_queries:
        query_ids = sorted({
            str(query.get("urn") or query.get("name") or "DataHub query evidence")
            for query in usage_queries
        })
        findings.append(Finding(
            "high",
            "ACTIVE_QUERY_USAGE",
            f"DataHub records {len(query_ids)} active query pattern(s) affected by the destructive change.",
            query_ids,
        ))
    if _SELECT_STAR_RE.search(executable_sql):
        findings.append(Finding(
            "medium",
            "UNSTABLE_PROJECTION",
            "SELECT * couples the change to future schema drift; enumerate governed fields.",
            urns,
        ))
    if not urns:
        findings.append(Finding(
            "high",
            "UNRESOLVED_ASSET",
            "No referenced table could be resolved in DataHub.",
            names or ["No table reference detected"],
        ))

    weights = {"critical": 55, "high": 30, "medium": 15, "low": 5}
    score = min(100, sum(weights[f.severity] for f in findings))
    verdict = "BLOCK" if score >= 50 else "REVIEW" if findings else "PASS"
    safer_sql = sql
    if _SELECT_STAR_RE.search(executable_sql):
        # Only rewrite an executable SELECT *, never an example embedded in a
        # comment or string. The first executable match has the same offsets as
        # the original because `_executable_sql` preserves span lengths.
        match = _SELECT_STAR_RE.search(executable_sql)
        assert match is not None
        safer_sql = (
            safer_sql[: match.start()]
            + "SELECT /* enumerate approved fields */"
            + safer_sql[match.end() :]
        )
    if destructive_change and downstream:
        # Disable every source line after performing position-sensitive
        # rewrites. Prefixing first would invalidate offsets; prefixing only the
        # first line would leave later destructive statements executable.
        disabled_sql = "\n".join(f"-- {line}" for line in safer_sql.splitlines())
        safer_sql = (
            "-- ContractGuard: stage a compatibility view and notify downstream owners first.\n"
            + disabled_sql
        )

    lines = [
        "# ContractGuard decision",
        "",
        f"- Verdict: **{verdict}**",
        f"- Risk score: **{score}/100**",
        f"- Resolved DataHub assets: {len(urns)}",
        f"- DataHub usage queries inspected: {len(usage_queries)}",
        "",
        "## Findings",
    ]
    lines.extend(
        f"- **{f.severity.upper()} · {f.code}** — {f.message}" for f in findings
    )
    lines.extend(["", "## Safer migration", "```sql", safer_sql, "```"])
    markdown = "\n".join(lines)
    writeback_id = None
    if write_back:
        writeback_id = catalog.save_decision(
            f"ContractGuard: {verdict} SQL change",
            markdown,
            urns,
        )
    return Review(verdict, score, urns, findings, safer_sql, markdown, writeback_id)
