# Live Opportunity Research Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a reusable CLI workflow for analyzing recorded live Polymarket books and measuring how often sub-1.00 full-set opportunities appear.

**Architecture:** Keep `record-live` unchanged as the capture layer. Add a small research module that replays recorded order-book events into paired market state, computes raw and post-cost full-set sums, and writes a summary report through the existing reporting layer. Ship a separate multi-market research config so longer live sessions can be run without editing the sample single-market config.

**Tech Stack:** Python 3.9+, `typer`, `pydantic`, JSON reporting, `pytest`

---

## File Structure

### Files To Modify

- Modify: `src/polymarket_arb/cli.py`
  Add the new analysis command.
- Modify: `src/polymarket_arb/reporting/writers.py`
  Add writer support for the opportunity research summary.
- Modify: `README.md`
  Document the multi-market research workflow.

### Files To Create

- Create: `src/polymarket_arb/research/opportunities.py`
  Implement the recorded-run analyzer and result models.
- Create: `configs/markets.research.yaml`
  Curated active-slug config for longer live capture sessions.
- Create: `tests/unit/research/test_opportunities.py`
  Unit tests for paired-book aggregation and opportunity metrics.
- Create: `tests/integration/test_analyze_recording_cli.py`
  End-to-end CLI test for the new command.

## Task 1: Add Analyzer Unit Tests

**Files:**
- Create: `tests/unit/research/test_opportunities.py`
- Create: `src/polymarket_arb/research/opportunities.py`

- [ ] **Step 1: Write the failing unit tests**

```python
from polymarket_arb.domain.events import OrderBookEvent
from polymarket_arb.domain.models import BookLevel, MarketCatalogEntry
from polymarket_arb.research.opportunities import analyze_recorded_opportunities


def test_analyzer_counts_raw_and_post_cost_opportunities() -> None:
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
    events = [
        OrderBookEvent(
            market_id="m1",
            side="YES",
            asks=[BookLevel(price=0.48, size=100)],
            timestamp_ms=1_000,
        ),
        OrderBookEvent(
            market_id="m1",
            side="NO",
            asks=[BookLevel(price=0.49, size=100)],
            timestamp_ms=1_000,
        ),
        OrderBookEvent(
            market_id="m1",
            side="YES",
            asks=[BookLevel(price=0.52, size=100)],
            timestamp_ms=2_000,
        ),
        OrderBookEvent(
            market_id="m1",
            side="NO",
            asks=[BookLevel(price=0.50, size=100)],
            timestamp_ms=2_000,
        ),
    ]

    report = analyze_recorded_opportunities(
        catalog=catalog,
        events=events,
        stale_after_ms=5_000,
        fee_rate=0.005,
        slippage_buffer=0.002,
        operational_buffer=0.001,
    )

    assert report.event_count == 4
    assert report.paired_snapshot_count == 3
    assert report.raw_opportunity_count == 1
    assert report.post_cost_opportunity_count == 1
    assert report.markets[0].slug == "market-one"
    assert report.markets[0].best_raw_sum == 0.97
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src /Users/alphaartrem/Desktop/workspace/trading_bot/.venv/bin/pytest tests/unit/research/test_opportunities.py -v`
Expected: FAIL because the research analyzer module does not exist yet.

- [ ] **Step 3: Implement the minimal analyzer**

Implement models and `analyze_recorded_opportunities()` in `src/polymarket_arb/research/opportunities.py`.

- [ ] **Step 4: Run the unit test to verify it passes**

Run: `PYTHONPATH=src /Users/alphaartrem/Desktop/workspace/trading_bot/.venv/bin/pytest tests/unit/research/test_opportunities.py -v`
Expected: PASS

## Task 2: Add CLI Coverage For Recorded Analysis

**Files:**
- Create: `tests/integration/test_analyze_recording_cli.py`
- Modify: `src/polymarket_arb/cli.py`
- Modify: `src/polymarket_arb/reporting/writers.py`

- [ ] **Step 1: Write the failing CLI integration test**

The test should create a run directory with `catalog.json` and `events.jsonl`, invoke:

```bash
analyze-recording --config-path <config> --run-dir <run_dir> --output-dir <output_dir>
```

and assert that `opportunity_summary.json` exists and contains nonzero paired snapshot counts.

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src /Users/alphaartrem/Desktop/workspace/trading_bot/.venv/bin/pytest tests/integration/test_analyze_recording_cli.py -v`
Expected: FAIL because the CLI command and writer do not exist yet.

- [ ] **Step 3: Add the CLI command and report writer**

Wire the command through `JsonlEventStore`, `load_settings()`, and the analyzer. Write the result as `opportunity_summary.json`.

- [ ] **Step 4: Run the CLI test to verify it passes**

Run: `PYTHONPATH=src /Users/alphaartrem/Desktop/workspace/trading_bot/.venv/bin/pytest tests/integration/test_analyze_recording_cli.py -v`
Expected: PASS

## Task 3: Add A Multi-Market Research Config And Docs

**Files:**
- Create: `configs/markets.research.yaml`
- Modify: `README.md`

- [ ] **Step 1: Add the research config**

Create a config with a curated list of active binary slugs and conservative per-market caps.

- [ ] **Step 2: Document the workflow**

Add commands for:

```bash
PYTHONPATH=src /Users/alphaartrem/Desktop/workspace/trading_bot/.venv/bin/python -m polymarket_arb.cli record-live --config-path configs/markets.research.yaml --run-dir artifacts/research-live --duration-seconds 1800
PYTHONPATH=src /Users/alphaartrem/Desktop/workspace/trading_bot/.venv/bin/python -m polymarket_arb.cli analyze-recording --config-path configs/markets.research.yaml --run-dir artifacts/research-live --output-dir artifacts/research-report
```

- [ ] **Step 3: Run focused tests plus full suite**

Run: `PYTHONPATH=src /Users/alphaartrem/Desktop/workspace/trading_bot/.venv/bin/pytest tests/unit/research/test_opportunities.py tests/integration/test_analyze_recording_cli.py -v`
Expected: PASS

Run: `PYTHONPATH=src /Users/alphaartrem/Desktop/workspace/trading_bot/.venv/bin/pytest -v`
Expected: PASS

## Task 4: Verify The Real Research Workflow

**Files:**
- Modify: `configs/markets.research.yaml`
- Verify: `artifacts/research-live`
- Verify: `artifacts/research-report`

- [ ] **Step 1: Run a short live capture with the research config**

Run: `PYTHONPATH=src /Users/alphaartrem/Desktop/workspace/trading_bot/.venv/bin/python -m polymarket_arb.cli record-live --config-path configs/markets.research.yaml --run-dir artifacts/research-live --duration-seconds 5`
Expected: writes a multi-market `catalog.json` and non-empty `events.jsonl`

- [ ] **Step 2: Run the analysis command on the captured run**

Run: `PYTHONPATH=src /Users/alphaartrem/Desktop/workspace/trading_bot/.venv/bin/python -m polymarket_arb.cli analyze-recording --config-path configs/markets.research.yaml --run-dir artifacts/research-live --output-dir artifacts/research-report`
Expected: writes `opportunity_summary.json`

- [ ] **Step 3: Inspect the report**

Confirm the report includes run totals and per-market counts.
