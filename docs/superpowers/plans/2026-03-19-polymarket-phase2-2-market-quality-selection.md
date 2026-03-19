# Polymarket Phase 2.2 Market Quality And Selection Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a shared live and replay market-quality analysis layer that measures per-market opportunity frequency and persistence, then classifies markets as `keep`, `watch`, or `drop`.

**Architecture:** Keep the existing live adapter and trading engine intact. Add explicit research settings plus a dedicated market-quality tracker that consumes normalized order book events, derives paired-book opportunity windows, and writes deterministic research artifacts. Expose the tracker through one new live-study CLI command and by upgrading recorded-run analysis to use the same core logic.

**Tech Stack:** Python 3.11+, `pydantic`, `typer`, `pytest`, `pytest-asyncio`, JSON reporting

---

## Scope Check

This plan intentionally covers:

- config-driven market-quality thresholds
- per-market live activity and opportunity-persistence metrics
- deterministic `keep` / `watch` / `drop` classification
- shared analysis across live stream runs and recorded events
- run summary and per-market machine-readable artifacts
- docs updates for the new phase ordering and CLI workflow

This plan does not include:

- richer fill simulation
- lot-level accounting
- execution realism beyond current paired-book observation
- real-money execution
- automated market discovery outside the configured universe

## File Structure

### Files To Modify

- Modify: `src/polymarket_arb/config.py`
  Add research-threshold settings to the main config model.
- Modify: `configs/markets.sample.yaml`
  Show the new research settings in the general sample config.
- Modify: `configs/markets.research.yaml`
  Provide a VPS-ready research config with Phase 2.2 thresholds.
- Modify: `src/polymarket_arb/research/opportunities.py`
  Reuse the new shared market-quality tracker for recorded-event analysis.
- Modify: `src/polymarket_arb/cli.py`
  Add `study-live-opportunities` and upgrade `analyze-recording` to emit market-quality artifacts.
- Modify: `src/polymarket_arb/reporting/writers.py`
  Persist run summary and per-market market-quality reports.
- Modify: `tests/unit/test_config.py`
  Cover the new research settings.
- Modify: `tests/unit/research/test_opportunities.py`
  Cover richer replay-market-quality outputs.
- Modify: `tests/integration/test_analyze_recording_cli.py`
  Assert recorded-run analysis writes the new artifacts.
- Modify: `tests/unit/test_cli.py`
  Assert help lists the new research command.
- Modify: `README.md`
  Document how to run live market studies and interpret the classification output.
- Modify: `docs/superpowers/plans/2026-03-18-polymarket-roadmap.md`
  Insert Phase 2.2 between Phase 2.1 and Phase 3.

### Files To Create

- Create: `src/polymarket_arb/research/market_quality.py`
  Shared tracker, report models, duration math, and classification logic.
- Create: `tests/unit/research/test_market_quality.py`
  Unit tests for window tracking, duration stats, and classification rules.
- Create: `tests/integration/test_study_live_opportunities_cli.py`
  Integration test for the live market-study CLI.

## Task 1: Add Research Threshold Settings

**Files:**
- Modify: `src/polymarket_arb/config.py`
- Modify: `configs/markets.sample.yaml`
- Modify: `configs/markets.research.yaml`
- Modify: `tests/unit/test_config.py`

- [ ] **Step 1: Write the failing config test**

```python
from pathlib import Path
from textwrap import dedent

from polymarket_arb.config import load_settings


def test_load_settings_reads_research_thresholds(tmp_path: Path) -> None:
    config_path = tmp_path / "research.yaml"
    config_path.write_text(
        dedent(
            """
            venue: polymarket
            api:
              gamma_base_url: https://gamma-api.polymarket.com
              clob_base_url: https://clob.polymarket.com
              poll_interval_ms: 500
            research:
              keep_min_paired_snapshots_per_minute: 8
              keep_min_post_cost_opportunities_per_minute: 1
              keep_min_total_time_in_edge_ms: 3000
              keep_min_best_net_edge_bps: 15
              keep_min_max_window_ms: 1500
              watch_min_paired_snapshots_per_minute: 3
              watch_min_post_cost_opportunities_per_minute: 0.2
              watch_min_best_net_edge_bps: 5
              low_sample_paired_snapshot_floor: 5
            markets:
              - slug: market-one
                max_capital_usd: 50
            strategy:
              raw_alert_threshold: 0.99
              fee_rate: 0.005
              slippage_buffer: 0.002
              operational_buffer: 0.001
              stale_after_ms: 5000
            portfolio:
              starting_cash_usd: 500
              max_total_deployed_usd: 200
            """
        ).strip()
    )

    settings = load_settings(config_path)

    assert settings.research.keep_min_best_net_edge_bps == 15
    assert settings.research.watch_min_post_cost_opportunities_per_minute == 0.2
    assert settings.research.low_sample_paired_snapshot_floor == 5
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src .venv/bin/pytest tests/unit/test_config.py::test_load_settings_reads_research_thresholds -v`
Expected: FAIL because `Settings` has no `research` section yet.

- [ ] **Step 3: Add minimal research settings models**

```python
class ResearchSettings(BaseModel):
    keep_min_paired_snapshots_per_minute: float = Field(ge=0)
    keep_min_post_cost_opportunities_per_minute: float = Field(ge=0)
    keep_min_total_time_in_edge_ms: int = Field(ge=0)
    keep_min_best_net_edge_bps: float = Field(ge=0)
    keep_min_max_window_ms: int = Field(ge=0)
    watch_min_paired_snapshots_per_minute: float = Field(ge=0)
    watch_min_post_cost_opportunities_per_minute: float = Field(ge=0)
    watch_min_best_net_edge_bps: float = Field(ge=0)
    low_sample_paired_snapshot_floor: int = Field(ge=0)


class Settings(BaseModel):
    ...
    research: ResearchSettings = ResearchSettings(
        keep_min_paired_snapshots_per_minute=0,
        keep_min_post_cost_opportunities_per_minute=0,
        keep_min_total_time_in_edge_ms=0,
        keep_min_best_net_edge_bps=0,
        keep_min_max_window_ms=0,
        watch_min_paired_snapshots_per_minute=0,
        watch_min_post_cost_opportunities_per_minute=0,
        watch_min_best_net_edge_bps=0,
        low_sample_paired_snapshot_floor=0,
    )
```

- [ ] **Step 4: Update sample configs**

Add a `research:` block to both config files.

```yaml
research:
  keep_min_paired_snapshots_per_minute: 8
  keep_min_post_cost_opportunities_per_minute: 1
  keep_min_total_time_in_edge_ms: 3000
  keep_min_best_net_edge_bps: 15
  keep_min_max_window_ms: 1500
  watch_min_paired_snapshots_per_minute: 3
  watch_min_post_cost_opportunities_per_minute: 0.2
  watch_min_best_net_edge_bps: 5
  low_sample_paired_snapshot_floor: 5
```

- [ ] **Step 5: Run the config tests**

Run: `PYTHONPATH=src .venv/bin/pytest tests/unit/test_config.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/polymarket_arb/config.py configs/markets.sample.yaml configs/markets.research.yaml tests/unit/test_config.py
git commit -m "feat: add market quality research settings"
```

## Task 2: Add Shared Market Quality Tracker And Duration Math

**Files:**
- Create: `src/polymarket_arb/research/market_quality.py`
- Create: `tests/unit/research/test_market_quality.py`

- [ ] **Step 1: Write the failing tracker test**

```python
from polymarket_arb.domain.events import OrderBookEvent
from polymarket_arb.domain.models import BookLevel, MarketCatalogEntry
from polymarket_arb.research.market_quality import MarketQualityTracker


def test_market_quality_tracker_counts_windows_and_edge_time() -> None:
    catalog = [
        MarketCatalogEntry(
            market_id="m1",
            slug="market-one",
            question="Market one?",
            yes_token_id="yes-1",
            no_token_id="no-1",
            fees_enabled=False,
            max_capital_usd=50,
            active=True,
        )
    ]
    tracker = MarketQualityTracker(
        catalog=catalog,
        stale_after_ms=5_000,
        fee_rate=0.005,
        slippage_buffer=0.002,
        operational_buffer=0.001,
    )

    tracker.observe(
        OrderBookEvent(
            market_id="m1",
            side="YES",
            asks=[BookLevel(price=0.48, size=100.0)],
            timestamp_ms=1_000,
        )
    )
    tracker.observe(
        OrderBookEvent(
            market_id="m1",
            side="NO",
            asks=[BookLevel(price=0.49, size=100.0)],
            timestamp_ms=1_000,
        )
    )
    tracker.observe(
        OrderBookEvent(
            market_id="m1",
            side="YES",
            asks=[BookLevel(price=0.48, size=100.0)],
            timestamp_ms=3_000,
        )
    )
    tracker.observe(
        OrderBookEvent(
            market_id="m1",
            side="NO",
            asks=[BookLevel(price=0.55, size=100.0)],
            timestamp_ms=7_000,
        )
    )

    report = tracker.finalize(run_duration_seconds=7)
    market = report.markets[0]

    assert market.post_cost_opportunity_count == 2
    assert market.opportunity_window_count == 1
    assert market.total_time_in_edge_ms == 6_000
    assert market.max_window_ms == 6_000
```

- [ ] **Step 2: Write the failing duration-summary test**

```python
from polymarket_arb.research.market_quality import summarize_window_durations


def test_summarize_window_durations_returns_percentiles() -> None:
    summary = summarize_window_durations([500, 1_500, 4_000])

    assert summary["p50_window_ms"] == 1_500
    assert summary["p95_window_ms"] == 4_000
    assert summary["max_window_ms"] == 4_000
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `PYTHONPATH=src .venv/bin/pytest tests/unit/research/test_market_quality.py -v`
Expected: FAIL because the tracker module does not exist.

- [ ] **Step 4: Add the shared tracker and report models**

Implement focused Pydantic models in `src/polymarket_arb/research/market_quality.py`:

```python
class MarketQualityRecord(BaseModel):
    market_id: str
    slug: str
    question: str
    message_count: int = 0
    paired_snapshot_count: int = 0
    stale_snapshot_count: int = 0
    raw_opportunity_count: int = 0
    post_cost_opportunity_count: int = 0
    best_raw_sum: float | None = None
    best_net_sum: float | None = None
    best_net_edge_bps: float = 0.0
    opportunity_window_count: int = 0
    total_time_in_edge_ms: int = 0
    p50_window_ms: float = 0.0
    p95_window_ms: float = 0.0
    max_window_ms: float = 0.0
    status: str = "drop"
    reasons: list[str] = []


class MarketQualityReport(BaseModel):
    event_count: int
    paired_snapshot_count: int
    raw_opportunity_count: int
    post_cost_opportunity_count: int
    opportunity_window_count: int
    markets: list[MarketQualityRecord]
```

Implement a tracker with three explicit methods:

```python
class MarketQualityTracker:
    def observe(self, event: OrderBookEvent) -> None: ...
    def note_stream_message(self) -> None: ...
    def finalize(self, *, run_duration_seconds: float) -> MarketQualityReport: ...
```

- [ ] **Step 5: Run the new unit tests**

Run: `PYTHONPATH=src .venv/bin/pytest tests/unit/research/test_market_quality.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/polymarket_arb/research/market_quality.py tests/unit/research/test_market_quality.py
git commit -m "feat: add market quality tracker"
```

## Task 3: Add Classification Rules And Recorded-Run Reuse

**Files:**
- Modify: `src/polymarket_arb/research/opportunities.py`
- Modify: `tests/unit/research/test_opportunities.py`

- [ ] **Step 1: Write the failing classification test**

Extend the recorded-analysis test to assert classification output:

```python
assert report.markets[0].status == "keep"
assert "passes_keep_thresholds" in report.markets[0].reasons
assert report.markets[0].best_net_edge_bps == 22
```

- [ ] **Step 2: Add a second failing test for quiet markets**

```python
def test_analyzer_classifies_quiet_market_as_drop() -> None:
    ...
    assert report.markets[0].status == "drop"
    assert "too_quiet" in report.markets[0].reasons
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `PYTHONPATH=src .venv/bin/pytest tests/unit/research/test_opportunities.py -v`
Expected: FAIL because the recorded analyzer does not expose classification fields yet.

- [ ] **Step 4: Rebuild recorded analysis on top of the shared tracker**

Keep the public entry point, but delegate to the tracker:

```python
def analyze_recorded_opportunities(
    *,
    catalog: list[MarketCatalogEntry],
    events: list[OrderBookEvent],
    stale_after_ms: int,
    fee_rate: float,
    slippage_buffer: float,
    operational_buffer: float,
    research: ResearchSettings,
) -> MarketQualityReport:
    tracker = MarketQualityTracker(
        catalog=catalog,
        stale_after_ms=stale_after_ms,
        fee_rate=fee_rate,
        slippage_buffer=slippage_buffer,
        operational_buffer=operational_buffer,
        research=research,
    )
    for event in events:
        tracker.observe(event)
    return tracker.finalize(
        run_duration_seconds=_duration_seconds(events),
    )
```

The classification layer should stay deterministic and reason-based:

```python
if record.paired_snapshot_count < research.low_sample_paired_snapshot_floor:
    reasons.append("too_quiet")
elif record.post_cost_opportunity_count == 0:
    reasons.append("no_post_cost_edge")
elif keep_thresholds_met:
    reasons.append("passes_keep_thresholds")
    status = "keep"
elif watch_thresholds_met:
    reasons.append("passes_watch_thresholds")
    status = "watch"
else:
    reasons.append("edge_too_brief")
```

- [ ] **Step 5: Run the replay-analysis unit tests**

Run: `PYTHONPATH=src .venv/bin/pytest tests/unit/research/test_opportunities.py tests/unit/research/test_market_quality.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/polymarket_arb/research/opportunities.py tests/unit/research/test_opportunities.py
git commit -m "feat: classify recorded market quality"
```

## Task 4: Add Writers And Research CLI Commands

**Files:**
- Modify: `src/polymarket_arb/cli.py`
- Modify: `src/polymarket_arb/reporting/writers.py`
- Modify: `tests/integration/test_analyze_recording_cli.py`
- Modify: `tests/unit/test_cli.py`
- Create: `tests/integration/test_study_live_opportunities_cli.py`

- [ ] **Step 1: Write the failing live-study CLI test**

```python
def test_study_live_opportunities_writes_market_quality_artifacts(
    tmp_path: Path, monkeypatch
) -> None:
    ...
    result = runner.invoke(
        app,
        [
            "study-live-opportunities",
            "--config-path",
            str(config_path),
            "--output-dir",
            str(output_dir),
            "--duration-seconds",
            "1",
            "--mode",
            "stream",
        ],
    )

    assert result.exit_code == 0
    summary = json.loads(
        (output_dir / "market_quality_summary.json").read_text(encoding="utf-8")
    )
    by_market = json.loads(
        (output_dir / "market_quality_by_market.json").read_text(encoding="utf-8")
    )
    assert summary["classification_counts"]["keep"] == 1
    assert by_market[0]["status"] == "keep"
```

- [ ] **Step 2: Write the failing recorded-analysis CLI assertion**

Update `tests/integration/test_analyze_recording_cli.py` to assert:

```python
summary = json.loads(
    (output_dir / "market_quality_summary.json").read_text(encoding="utf-8")
)
by_market = json.loads(
    (output_dir / "market_quality_by_market.json").read_text(encoding="utf-8")
)
assert summary["classification_counts"]["keep"] == 1
assert by_market[0]["best_net_edge_bps"] == 22
```

- [ ] **Step 3: Run the integration tests to verify they fail**

Run: `PYTHONPATH=src .venv/bin/pytest tests/integration/test_analyze_recording_cli.py tests/integration/test_study_live_opportunities_cli.py tests/unit/test_cli.py -v`
Expected: FAIL because the new command and artifact writers do not exist yet.

- [ ] **Step 4: Add market-quality writer helpers**

In `src/polymarket_arb/reporting/writers.py`, add:

```python
def write_market_quality_summary(output_dir: Path, payload: dict[str, Any]) -> Path:
    ...


def write_market_quality_by_market(output_dir: Path, payload: list[dict[str, Any]]) -> Path:
    ...
```

- [ ] **Step 5: Add `study-live-opportunities` and upgrade `analyze-recording`**

Add a dedicated CLI command:

```python
@app.command("study-live-opportunities")
def study_live_opportunities(
    config_path: Path = typer.Option(..., "--config-path"),
    output_dir: Path = typer.Option(..., "--output-dir"),
    duration_seconds: int = typer.Option(300, "--duration-seconds"),
    mode: str | None = typer.Option("stream", "--mode"),
) -> None:
    ...
```

Implementation notes:

- refresh catalog
- build the live adapter in stream mode
- instantiate the tracker once
- call `tracker.note_stream_message()` when raw stream frames are observed, if the adapter exposes that count
- feed each normalized event into `tracker.observe(event)`
- finalize with real run duration
- write:
  - `market_quality_summary.json`
  - `market_quality_by_market.json`
  - `feed_health.json`

Also upgrade `analyze-recording` to use the same shared report and write the same two artifacts for recorded runs.

- [ ] **Step 6: Update CLI help expectations**

In `tests/unit/test_cli.py`, assert the new command is listed:

```python
assert "study-live-opportunities" in result.stdout
```

- [ ] **Step 7: Run the CLI and writer tests**

Run: `PYTHONPATH=src .venv/bin/pytest tests/integration/test_analyze_recording_cli.py tests/integration/test_study_live_opportunities_cli.py tests/unit/test_cli.py -v`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add src/polymarket_arb/cli.py src/polymarket_arb/reporting/writers.py tests/integration/test_analyze_recording_cli.py tests/integration/test_study_live_opportunities_cli.py tests/unit/test_cli.py
git commit -m "feat: add market quality research commands"
```

## Task 5: Update Docs, Roadmap, And Final Verification

**Files:**
- Modify: `README.md`
- Modify: `docs/superpowers/plans/2026-03-18-polymarket-roadmap.md`

- [ ] **Step 1: Update the roadmap ordering**

Insert Phase 2.2 after Phase 2.1:

```markdown
1. [Phase 2.1: VPS And Low-Latency Market Data](...)
2. [Phase 2.2: Market Quality And Selection](...)
3. [Phase 3: Execution Accounting And Research Artifacts](...)
```

Update dependency notes so they explicitly say Phase 2.2 should happen before deeper Phase 3 accounting work, because it narrows the live market universe using real streamed evidence.

- [ ] **Step 2: Update README usage docs**

Document:

- the `study-live-opportunities` command
- the meaning of `keep`, `watch`, and `drop`
- the new artifact files
- the intended workflow:
  - run live study on VPS
  - review classifications
  - narrow the market universe
  - then proceed to deeper paper-trading and accounting phases

- [ ] **Step 3: Run focused verification**

Run:

```bash
PYTHONPATH=src .venv/bin/pytest \
  tests/unit/test_config.py \
  tests/unit/research/test_market_quality.py \
  tests/unit/research/test_opportunities.py \
  tests/unit/test_cli.py \
  tests/integration/test_analyze_recording_cli.py \
  tests/integration/test_study_live_opportunities_cli.py -v
```

Expected: PASS

- [ ] **Step 4: Run CLI smoke checks**

Run:

```bash
PYTHONPATH=src .venv/bin/python -m polymarket_arb.cli study-live-opportunities --help
PYTHONPATH=src .venv/bin/python -m polymarket_arb.cli analyze-recording --help
```

Expected: both commands print help and exit `0`

- [ ] **Step 5: Commit**

```bash
git add README.md docs/superpowers/plans/2026-03-18-polymarket-roadmap.md
git commit -m "docs: describe phase 2.2 market quality workflow"
```

## Notes For Execution

- Keep this phase separate from `run-paper`. The research command should observe market quality without pretending to simulate better execution than we actually have.
- Do not make the classification heuristic-heavy. Thresholds and emitted reasons should stay auditable from config and artifacts.
- Prefer one shared tracker core for both live and replay paths. The live CLI and recorded-run analysis should differ only at the event source boundary.
