# Live Opportunity Research Design

## Goal

Add a reusable workflow for measuring how often live Polymarket full-set opportunities appear in recorded order books, instead of relying on ad hoc shell commands or one-off scripts.

## Approaches Considered

### Recommended: Record first, analyze recorded runs through a CLI command

Keep `record-live` responsible for capture and add a separate analysis command that reads `catalog.json` and `events.jsonl`, reconstructs paired YES/NO best asks per market, and writes a research report. This keeps the research logic deterministic and rerunnable across any captured run directory.

### Alternative: One-off script in `scripts/`

This would be fast to write but easy to lose, harder to test, and likely to diverge from the CLI and reporting patterns already used in the repo.

### Alternative: Fold research metrics into `run-paper`

This would reuse existing live polling, but it would mix research reporting with trading-engine behavior. The engine currently measures trades and rejections, not market microstructure frequency, so coupling them would make both paths harder to reason about.

## Decision

Implement a dedicated research command and report path.

The workflow will be:

1. Refresh or maintain a curated multi-market config.
2. Run a longer `record-live` session.
3. Run a new CLI command over the captured run directory to produce a machine-readable opportunity report.

## Data Model

The analysis only needs the existing recorded artifacts:

- `catalog.json` for market metadata and slug mapping
- `events.jsonl` for timestamped YES/NO ask books

For each market, the analyzer will maintain the latest paired YES and NO books, similar to the runtime state store. On each event where both sides are fresh:

- compute `raw_sum = best_yes_ask + best_no_ask`
- compute `net_sum = raw_sum + fee_rate + slippage_buffer + operational_buffer`
- classify whether the snapshot is:
  - raw opportunity (`raw_sum < 1.0`)
  - post-cost opportunity (`net_sum < 1.0`)

## Output

Write a report directory containing:

- `opportunity_summary.json`
- per-market metrics embedded in the summary

The summary should include:

- run-level event count
- count of paired snapshots evaluated
- count of raw opportunities
- count of post-cost opportunities
- per-market counts for paired snapshots, raw opportunities, and post-cost opportunities
- per-market best observed `raw_sum` and `net_sum`

This gives enough evidence to decide whether longer capture windows or execution changes are justified.

## CLI Surface

Add a command:

`analyze-recording --config-path <config> --run-dir <run_dir> --output-dir <output_dir>`

The command will:

1. load settings for the cost buffers
2. validate replay inputs
3. analyze the recorded order books
4. write the opportunity summary report

## Config

Add a new sample research config with multiple active slugs curated from current public Gamma data. This config is for experimentation, not production execution.

## Testing

Add:

- unit tests for the analyzer math and per-market aggregation
- an integration CLI test for `analyze-recording`

## Error Handling

- Missing `catalog.json` or `events.jsonl` should fail through existing replay-input validation.
- Markets with only one side observed should not count as paired snapshots.
- Empty ask books should be skipped for opportunity checks.
