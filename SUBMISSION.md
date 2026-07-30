# Devpost submission draft

## Title

ContractGuard — Metadata-aware SQL change review with DataHub

## One-line pitch

Stop breaking data changes before merge by grounding code review in real
DataHub schema, lineage and usage—and preserving the decision in the catalog.

## Inspiration

Code reviewers can see a migration diff but rarely know every dashboard, model
or analyst query downstream. DataHub already has that organizational context;
ContractGuard turns it into an executable safety gate.

## What it does

ContractGuard reads a SQL or dbt change, resolves referenced assets through
DataHub MCP, measures downstream blast radius, detects unstable projections and
deprecated assets, and returns a PASS, REVIEW or BLOCK decision. It generates a
safer migration and writes the evidence-backed decision to a DataHub document.

## How we built it

The policy engine is a dependency-free Python core. A catalog adapter separates
analysis from transport. The live adapter targets DataHub's official MCP tools;
a deterministic fixture adapter makes judging and tests reproducible.

## Challenges

The central design challenge was avoiding generic lint rules. Each important
finding includes catalog evidence, so the result is explainable and specific
to the organization's real data graph.

## Accomplishments

- DataHub is in the critical path, not a decorative lookup.
- The agent closes the loop by writing a durable decision back to DataHub.
- Reproducible tests cover breaking lineage and writeback behavior.

## What's next

GitHub Check annotations, dbt manifest mapping, owner notifications, and a
DataHub Cloud-backed public demo.

