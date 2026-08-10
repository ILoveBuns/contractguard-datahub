# ContractGuard for DataHub

[![tests](https://github.com/ILoveBuns/contractguard-datahub/actions/workflows/test.yml/badge.svg)](https://github.com/ILoveBuns/contractguard-datahub/actions/workflows/test.yml)

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

Requires Python 3.11 or newer. From a fresh clone:

```bash
python3 -m pip install -e .
```

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

The 19-test suite covers breaking lineage, asset-wide query evidence for
whole-table drops, active column query usage, safe changes,
unresolved assets, unstable projections, SQL comment/string-literal isolation,
deduplication, writeback, fixture semantics, CLI safety gates, and the exact
five-tool MCP flow. GitHub Actions repeats the suite
on Python 3.11, 3.12, and 3.13 so the public submission evidence is independently
reproducible.

## Rebuild the narrated demo video

The submission video is generated from reproducible evidence rather than a
private catalog recording. With ImageMagick, Edge TTS, and FFmpeg available:

```bash
./make_demo_video.sh
```

The script creates a sub-three-minute 1080p H.264/AAC video in
`demo-output/` and prints its media-stream verification report.

## Official DataHub MCP server

The deterministic fixture-backed demo above has no runtime dependencies. To run
against a live DataHub Cloud or OSS instance, install `uv` if needed and launch
the official DataHub MCP server through `uvx`:

```bash
# Install uv if it is not already available.
curl -LsSf https://astral.sh/uv/install.sh | sh

# Configure the DataHub connection without storing credentials in the repository.
export DATAHUB_GMS_URL="<your-datahub-url>"
export DATAHUB_GMS_TOKEN="<your-datahub-token>"
export DATAHUB_MCP_COMMAND="uvx mcp-server-datahub@latest --transport stdio"
```

An existing standard DataHub CLI profile such as `~/.datahubenv` may provide the
connection settings instead. Environment variables are shown as the explicit,
portable setup. ContractGuard never stores catalog tokens in the repository.

For read-only discovery and risk analysis, use the live CLI mode. It starts the
configured official server with mutation tools disabled:

```bash
contractguard examples/breaking_change.sql --live-datahub \
  --output artifacts/live-review.json
```

To persist an approved decision, both writeback flags are intentionally
required; this prevents an ordinary review from enabling mutation tools:

```bash
contractguard examples/breaking_change.sql --live-datahub \
  --write-back --enable-mutations --output artifacts/live-review.json
```

The live writeback flow invokes `search`, `get_entities`, `get_lineage`,
`get_dataset_queries`, and `save_document`. Mutation support is explicitly
enabled only for that final writeback; the default client and all discovery and
risk analysis remain read-only.

## Hackathon track

Primary: **Metadata-Aware Code Generation & Development**  
Secondary: **Agents That Do Real Work**

## License

Apache-2.0.
