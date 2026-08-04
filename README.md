# ContractGuard for DataHub

ContractGuard is a metadata-aware SQL and dbt change reviewer for the
[DataHub Hackathon 2026](https://datahub.devpost.com/). It resolves referenced
assets in DataHub, inspects schema and downstream lineage, blocks breaking
changes, proposes a safer migration, and writes the review decision back to
DataHub as a document.

## Why DataHub is essential

A SQL parser can detect `DROP COLUMN`; it cannot know that the column feeds a
Looker retention dashboard and a finance LTV model. ContractGuard uses the
official DataHub MCP server:

1. `search` resolves SQL identifiers to governed assets.
2. `get_entities` retrieves schema, ownership and deprecation context.
3. `get_lineage` finds downstream blast radius.
4. `get_dataset_queries` supplies real usage evidence.
5. `save_document` writes the review and migration decision back to DataHub.

The included fixture adapter makes the workflow reproducible without claiming
that sample results came from a live catalog. `DataHubMCPCatalog` is the
production adapter and talks to the official server over MCP stdio JSON-RPC.

## Run the deterministic demo

```bash
python3 -m contractguard.cli examples/breaking_change.sql \
  --write-back --output artifacts/review.json
```

Expected verdict: `BLOCK`, because the dropped `email` column has two
downstream consumers and two recorded production query patterns. The suggested
migration calls for a compatibility view and owner notification.

Compare that result with a safe, explicitly projected change:

```bash
python3 -m contractguard.cli examples/safe_change.sql \
  --output artifacts/safe-review.json
```

Expected verdict: `PASS`. Both machine-readable outputs are committed so a
judge can inspect the evidence without installing anything.

## Test

```bash
python3 -m unittest discover -s tests -v
```

The 10-test suite covers breaking lineage, active query usage, safe changes,
unresolved assets, unstable projections, deduplication, writeback, fixture
semantics, and the exact five-tool MCP flow.

## Rebuild the narrated demo video

The submission video is generated from reproducible evidence rather than a
private catalog recording. With ImageMagick, Edge TTS, and FFmpeg available:

```bash
./make_demo_video.sh
```

The script creates a sub-three-minute 1080p H.264/AAC video in
`demo-output/` and prints its media-stream verification report.

## Official DataHub MCP server

Run the official server with mutation tools enabled:

```bash
TOOLS_IS_MUTATION_ENABLED=true mcp-server-datahub --transport stdio
```

Configure your standard DataHub CLI profile for the target DataHub Cloud or OSS
instance. ContractGuard never stores catalog tokens in the repository.

In Python, select the live adapter with:

```python
from contractguard.engine import review_sql
from contractguard.mcp_catalog import DataHubMCPCatalog, MCPClient

with MCPClient() as client:
    review = review_sql(sql, DataHubMCPCatalog(client), write_back=True)
```

The live flow invokes `search`, `get_entities`, `get_lineage`,
`get_dataset_queries`, and `save_document`. Mutation support is required only
for the final writeback; all discovery and risk analysis remains read-only.

## Hackathon track

Primary: **Metadata-Aware Code Generation & Development**  
Secondary: **Agents That Do Real Work**

## License

Apache-2.0.
