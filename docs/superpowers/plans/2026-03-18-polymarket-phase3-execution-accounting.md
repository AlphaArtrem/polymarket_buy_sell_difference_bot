# Polymarket Phase 3 Execution Accounting Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the current smoke-test engine into an honest execution simulator with lot-level accounting and artifact outputs suitable for serious replay analysis.

**Architecture:** Keep the shared replay/live engine shape, but replace the current boolean-style trade decision path with explicit opportunity records, fill records, inventory lots, and run artifacts. This phase remains paper-only; it improves truthfulness and observability, not speed or real-money execution.

**Tech Stack:** Python 3.9+, `typer`, `pydantic`, `pytest`, `pytest-asyncio`, JSON/CSV reporting

---

## Scope Check

This plan intentionally covers:

- richer opportunity evaluation outputs
- strict fill records with depth-aware pricing
- lot-level portfolio accounting
- lifecycle modeling for paired inventory
- structured run artifacts for trades, rejections, and open lots

This plan does not include:

- WebSocket ingestion
- authenticated order placement
- automatic merge transactions
- live deployment automation

## File Structure

### Files To Modify

- Modify: `src/polymarket_arb/domain/models.py`
  Add explicit models for opportunity decisions, fill breakdowns, inventory lots, and run summaries.
- Modify: `src/polymarket_arb/strategy/opportunity.py`
  Return a structured opportunity evaluation object instead of only a yes/no decision.
- Modify: `src/polymarket_arb/strategy/sizing.py`
  Return sizing diagnostics or structured sizing results rather than a single float.
- Modify: `src/polymarket_arb/sim/execution.py`
  Return leg-level fill details, average prices, and broken-pair reasons.
- Modify: `src/polymarket_arb/portfolio/ledger.py`
  Track paired lots, open inventory, and realized vs locked capital.
- Modify: `src/polymarket_arb/portfolio/lifecycle.py`
  Add an explicit v1 realization policy for resolution and a placeholder policy for merge.
- Modify: `src/polymarket_arb/engine.py`
  Emit structured outcomes and keep per-run artifact collections.
- Modify: `src/polymarket_arb/reporting/writers.py`
  Write summary plus trade log, rejection log, and open-lot snapshots.
- Modify: `src/polymarket_arb/cli.py`
  Persist richer outputs for `run-replay` and `run-paper`.
- Modify: `README.md`
  Document the new artifact set.

### Files To Create

- Create: `tests/unit/strategy/test_opportunity_records.py`
  Verify structured opportunity decisions and rejection reasons.
- Create: `tests/unit/strategy/test_sizing_records.py`
  Verify size computation and limit diagnostics.
- Create: `tests/unit/sim/test_execution_records.py`
  Verify fill breakdowns, VWAP, and broken-pair classification.
- Create: `tests/unit/portfolio/test_lots.py`
  Verify lot opening, locking, and realization behavior.
- Create: `tests/integration/test_run_artifacts.py`
  Verify replay and paper modes emit the expanded artifact set.
- Create: `tests/acceptance/test_phase3_accounting.py`
  Acceptance scenario for one successful pair and one rejected opportunity.

## Task 1: Add Structured Opportunity And Sizing Records

**Files:**
- Modify: `src/polymarket_arb/domain/models.py`
- Modify: `src/polymarket_arb/strategy/opportunity.py`
- Modify: `src/polymarket_arb/strategy/sizing.py`
- Create: `tests/unit/strategy/test_opportunity_records.py`
- Create: `tests/unit/strategy/test_sizing_records.py`

- [ ] **Step 1: Write the failing opportunity-record test**

```python
from polymarket_arb.strategy.opportunity import evaluate_opportunity


def test_evaluate_opportunity_returns_structured_accept_record() -> None:
    decision = evaluate_opportunity(
        yes_ask=0.43,
        no_ask=0.54,
        raw_alert_threshold=0.99,
        fee_rate=0.0,
        slippage_buffer=0.0,
        operational_buffer=0.0,
    )

    assert decision.accepted is True
    assert decision.gross_cost == 0.97
    assert decision.estimated_net_cost == 0.97
    assert decision.rejection_reason is None
```

- [ ] **Step 2: Write the failing sizing-record test**

```python
from polymarket_arb.strategy.sizing import compute_paired_size


def test_compute_paired_size_returns_limit_reason() -> None:
    result = compute_paired_size(
        yes_size=20,
        no_size=5,
        available_cash=500,
        per_market_cap_usd=50,
        remaining_deployable_usd=200,
        estimated_net_cost=0.97,
    )

    assert result.paired_size == 5
    assert result.limiting_factor == "no_depth"
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `PYTHONPATH=src .venv/bin/pytest tests/unit/strategy/test_opportunity_records.py tests/unit/strategy/test_sizing_records.py -v`
Expected: FAIL because the current code returns simple primitive values.

- [ ] **Step 4: Add minimal structured models**

```python
class OpportunityDecision(BaseModel):
    accepted: bool
    gross_cost: float
    estimated_fee_cost: float
    estimated_slippage_cost: float
    operational_buffer_cost: float
    estimated_net_cost: float
    rejection_reason: str | None = None


class SizingDecision(BaseModel):
    paired_size: float
    limiting_factor: str | None = None
```

- [ ] **Step 5: Return those models from the strategy functions**

```python
return OpportunityDecision(
    accepted=True,
    gross_cost=yes_ask + no_ask,
    estimated_fee_cost=fee_cost,
    estimated_slippage_cost=slippage_buffer,
    operational_buffer_cost=operational_buffer,
    estimated_net_cost=net_cost,
)
```

```python
return SizingDecision(
    paired_size=paired_size,
    limiting_factor="no_depth",
)
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `PYTHONPATH=src .venv/bin/pytest tests/unit/strategy/test_opportunity_records.py tests/unit/strategy/test_sizing_records.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add src/polymarket_arb/domain/models.py src/polymarket_arb/strategy/opportunity.py src/polymarket_arb/strategy/sizing.py tests/unit/strategy/test_opportunity_records.py tests/unit/strategy/test_sizing_records.py
git commit -m "feat: add structured opportunity and sizing records"
```

## Task 2: Add Fill Breakdown Records And Broken-Pair Diagnostics

**Files:**
- Modify: `src/polymarket_arb/domain/models.py`
- Modify: `src/polymarket_arb/sim/execution.py`
- Create: `tests/unit/sim/test_execution_records.py`

- [ ] **Step 1: Write the failing fill-record test**

```python
from polymarket_arb.domain.models import BookLevel
from polymarket_arb.sim.execution import simulate_strict_pair_fill


def test_simulate_strict_pair_fill_returns_leg_breakdown() -> None:
    fill = simulate_strict_pair_fill(
        yes_asks=[BookLevel(price=0.43, size=5), BookLevel(price=0.44, size=5)],
        no_asks=[BookLevel(price=0.54, size=10)],
        target_size=8,
    )

    assert fill.status == "filled"
    assert fill.yes_leg.filled_size == 8
    assert round(fill.yes_leg.average_price, 4) == 0.4338
    assert fill.no_leg.average_price == 0.54
```

- [ ] **Step 2: Write the failing broken-pair test**

```python
from polymarket_arb.domain.models import BookLevel
from polymarket_arb.sim.execution import simulate_strict_pair_fill


def test_simulate_strict_pair_fill_returns_reason_on_broken_pair() -> None:
    fill = simulate_strict_pair_fill(
        yes_asks=[BookLevel(price=0.43, size=2)],
        no_asks=[BookLevel(price=0.54, size=10)],
        target_size=5,
    )

    assert fill.status == "broken_pair"
    assert fill.rejection_reason == "insufficient_yes_depth"
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `PYTHONPATH=src .venv/bin/pytest tests/unit/sim/test_execution_records.py -v`
Expected: FAIL because the current fill model does not expose leg records.

- [ ] **Step 4: Add minimal fill models**

```python
class FillLeg(BaseModel):
    requested_size: float
    filled_size: float
    total_cost: float
    average_price: float


class FillRecord(BaseModel):
    status: str
    requested_size: float
    filled_size: float
    total_cost: float
    yes_leg: FillLeg | None = None
    no_leg: FillLeg | None = None
    rejection_reason: str | None = None
```

- [ ] **Step 5: Update the simulator to produce those records**

```python
if yes_available < target_size:
    return FillRecord(
        status="broken_pair",
        requested_size=target_size,
        filled_size=0.0,
        total_cost=0.0,
        rejection_reason="insufficient_yes_depth",
    )
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `PYTHONPATH=src .venv/bin/pytest tests/unit/sim/test_execution_records.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add src/polymarket_arb/domain/models.py src/polymarket_arb/sim/execution.py tests/unit/sim/test_execution_records.py
git commit -m "feat: add detailed fill records"
```

## Task 3: Replace Cash Counters With Lot-Level Portfolio Accounting

**Files:**
- Modify: `src/polymarket_arb/domain/models.py`
- Modify: `src/polymarket_arb/portfolio/ledger.py`
- Modify: `src/polymarket_arb/portfolio/lifecycle.py`
- Create: `tests/unit/portfolio/test_lots.py`

- [ ] **Step 1: Write the failing lot-accounting test**

```python
from polymarket_arb.portfolio.ledger import PortfolioLedger


def test_portfolio_ledger_tracks_open_lots_and_realizes_resolution_pnl() -> None:
    ledger = PortfolioLedger(starting_cash_usd=500, free_cash_usd=500)

    lot = ledger.open_pair(
        market_id="market-1",
        pair_size=10,
        total_cost=9.7,
        entry_timestamp_ms=1000,
    )
    ledger.resolve_lot(lot_id=lot.lot_id, payout=10.0, resolved_timestamp_ms=2000)

    assert ledger.free_cash_usd == 500.3
    assert ledger.realized_pnl_usd == 0.3
    assert ledger.open_lots == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src .venv/bin/pytest tests/unit/portfolio/test_lots.py -v`
Expected: FAIL because `open_pair` only mutates aggregate counters.

- [ ] **Step 3: Add minimal lot models**

```python
class InventoryLot(BaseModel):
    lot_id: str
    market_id: str
    pair_size: float
    total_cost: float
    expected_payout: float
    entry_timestamp_ms: int
    realized: bool = False
```

- [ ] **Step 4: Update the ledger API to open and resolve lots**

```python
def open_pair(self, *, market_id: str, pair_size: float, total_cost: float, entry_timestamp_ms: int) -> InventoryLot:
    lot = InventoryLot(...)
    self.open_lots.append(lot)
    self.free_cash_usd -= total_cost
    self.locked_cost_basis_usd += total_cost
    return lot
```

- [ ] **Step 5: Add explicit realization logic**

```python
def resolve_lot(self, *, lot_id: str, payout: float, resolved_timestamp_ms: int) -> None:
    ...
```

- [ ] **Step 6: Run test to verify it passes**

Run: `PYTHONPATH=src .venv/bin/pytest tests/unit/portfolio/test_lots.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add src/polymarket_arb/domain/models.py src/polymarket_arb/portfolio/ledger.py src/polymarket_arb/portfolio/lifecycle.py tests/unit/portfolio/test_lots.py
git commit -m "feat: add lot-level portfolio accounting"
```

## Task 4: Emit Trade Logs, Rejection Logs, And Open-Lot Snapshots

**Files:**
- Modify: `src/polymarket_arb/engine.py`
- Modify: `src/polymarket_arb/reporting/writers.py`
- Modify: `src/polymarket_arb/cli.py`
- Create: `tests/integration/test_run_artifacts.py`
- Create: `tests/acceptance/test_phase3_accounting.py`

- [ ] **Step 1: Write the failing integration test**

```python
import json
from pathlib import Path

from typer.testing import CliRunner

from polymarket_arb.cli import app


def test_run_replay_writes_trade_rejection_and_open_lot_artifacts(tmp_path: Path) -> None:
    ...
    result = runner.invoke(app, [...])

    assert result.exit_code == 0
    assert (output_dir / "summary.json").exists()
    assert (output_dir / "trades.jsonl").exists()
    assert (output_dir / "rejections.jsonl").exists()
    assert (output_dir / "open_lots.json").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src .venv/bin/pytest tests/integration/test_run_artifacts.py tests/acceptance/test_phase3_accounting.py -v`
Expected: FAIL because only `summary.json` is written today.

- [ ] **Step 3: Update the engine to retain per-event outcomes**

```python
class EngineRunResult(BaseModel):
    summary: dict[str, float]
    trades: list[TradeRecord]
    rejections: list[RejectionRecord]
    open_lots: list[InventoryLot]
```

- [ ] **Step 4: Add artifact writers**

```python
def write_jsonl_records(output_path: Path, records: list[BaseModel]) -> Path:
    ...
```

- [ ] **Step 5: Wire replay and paper commands to write all artifacts**

```python
run_result = engine.run(...)
write_run_summary(output_dir, run_result.summary)
write_jsonl_records(output_dir / "trades.jsonl", run_result.trades)
write_jsonl_records(output_dir / "rejections.jsonl", run_result.rejections)
write_model_list(output_dir / "open_lots.json", run_result.open_lots)
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `PYTHONPATH=src .venv/bin/pytest tests/integration/test_run_artifacts.py tests/acceptance/test_phase3_accounting.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add src/polymarket_arb/engine.py src/polymarket_arb/reporting/writers.py src/polymarket_arb/cli.py tests/integration/test_run_artifacts.py tests/acceptance/test_phase3_accounting.py
git commit -m "feat: add run artifact outputs"
```

## Task 5: Verify The Full Phase

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Document the new artifacts**

```markdown
- `summary.json`
- `trades.jsonl`
- `rejections.jsonl`
- `open_lots.json`
```

- [ ] **Step 2: Run the focused verification suite**

Run: `PYTHONPATH=src .venv/bin/pytest tests/unit/strategy tests/unit/sim tests/unit/portfolio tests/integration/test_run_artifacts.py tests/acceptance/test_phase3_accounting.py -v`
Expected: PASS

- [ ] **Step 3: Run the full suite**

Run: `PYTHONPATH=src .venv/bin/pytest -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs: describe phase3 artifacts"
```
