from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any, Protocol


class Catalog(Protocol):
    def search(self, query: str) -> list[dict[str, Any]]: ...
    def entity(self, urn: str) -> dict[str, Any]: ...
    def lineage(self, urn: str) -> list[dict[str, Any]]: ...
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


_TABLE_RE = re.compile(r"\b(?:from|join|update|into|table)\s+([`\"\w.-]+)", re.I)
_DROP_RE = re.compile(r"\bdrop\s+(?:column\s+)?([`\"\w.-]+)", re.I)
_SELECT_STAR_RE = re.compile(r"\bselect\s+\*", re.I)


def _clean(value: str) -> str:
    return value.strip("`\"")


def review_sql(sql: str, catalog: Catalog, write_back: bool = False) -> Review:
    names = list(dict.fromkeys(_clean(x) for x in _TABLE_RE.findall(sql)))
    assets: list[dict[str, Any]] = []
    for name in names:
        assets.extend(catalog.search(name))

    findings: list[Finding] = []
    urns: list[str] = []
    downstream: list[str] = []
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

    dropped = [_clean(x) for x in _DROP_RE.findall(sql)]
    if dropped and downstream:
        findings.append(Finding(
            "critical",
            "BREAKING_LINEAGE",
            f"Dropping {', '.join(dropped)} can break {len(set(downstream))} downstream asset(s).",
            sorted(set(downstream)),
        ))
    if _SELECT_STAR_RE.search(sql):
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
    verdict = "BLOCK" if score >= 50 else "REVIEW" if score >= 20 else "PASS"
    safer_sql = sql
    if dropped and downstream:
        safer_sql = "-- ContractGuard: stage a compatibility view and notify downstream owners first.\n-- " + sql
    if _SELECT_STAR_RE.search(safer_sql):
        safer_sql = _SELECT_STAR_RE.sub("SELECT /* enumerate approved fields */", safer_sql)

    lines = [
        "# ContractGuard decision",
        "",
        f"- Verdict: **{verdict}**",
        f"- Risk score: **{score}/100**",
        f"- Resolved DataHub assets: {len(urns)}",
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

