# Polymarket Phase 2.4 Event Execution And Exit Accounting Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the Phase 2.3 event-paper path from a best-ask placeholder into an honest directional execution simulator with explicit exit policies, lifecycle accounting, and richer artifacts.

**Architecture:** Keep `src/polymarket_arb/research/event_paper.py` as the orchestration layer, but move fill realism into a dedicated directional execution simulator and move position lifecycle logic into a portfolio lifecycle module. Use structured records for fills, exits, rejections, and open positions so CLI artifacts and later live-readiness checks have one source of truth.

**Tech Stack:** Python 3.9+, `typer`, `pydantic`, `PyYAML`, `pytest`, JSON artifacts

---

## Scope Check

This plan is a single coherent follow-on to Phase 2.3. It tightens the honesty of the existing event-paper flow without touching authenticated trading, maker quoting, or structural arbitrage.

## File Structure

### Files To Modify

- Modify: `src/polymarket_arb/config.py`
  Extend event-research settings with exit and execution controls.
- Modify: `src/polymarket_arb/domain/models.py`
  Add structured records for directional fills, exits, rejections, and open positions.
- Modify: `src/polymarket_arb/portfolio/directional.py`
  Replace the minimal open/close ledger with a lot-aware directional ledger.
- Modify: `src/polymarket_arb/research/event_paper.py`
  Integrate depth-aware fills, partial exits, and lifecycle outcomes.
- Modify: `src/polymarket_arb/reporting/writers.py`
  Add richer Phase 2.4 artifact writers.
- Modify: `src/polymarket_arb/cli.py`
  Write the expanded artifact set from `run-event-paper`.
- Modify: `README.md`
  Document the richer event-paper outputs and controls.
- Modify: `tests/unit/test_config.py`
  Cover the new Phase 2.4 settings.
- Modify: `tests/unit/portfolio/test_directional_ledger.py`
  Extend current ledger coverage for partial exits and open positions.
- Modify: `tests/unit/research/test_event_paper.py`
  Extend current event-paper coverage for new lifecycle states.
- Modify: `tests/integration/test_run_event_paper_cli.py`
  Verify the richer artifact set end to end.

### Files To Create

- Create: `src/polymarket_arb/sim/directional.py`
  Depth-aware directional entry and exit fill simulator.
- Create: `src/polymarket_arb/portfolio/event_lifecycle.py`
  Exit policy and hold-to-resolution helpers.
- Create: `tests/unit/sim/test_directional_execution.py`
  Verify VWAP, partial fills, and broken exits.
- Create: `tests/unit/portfolio/test_event_lifecycle.py`
  Verify repricing, time-stop, and hold-to-resolution lifecycle decisions.
- Create: `tests/unit/research/test_event_execution_models.py`
  Verify new fill and rejection models.

## Task 1: Add Phase 2.4 Settings And Structured Records

**Files:**
- Modify: `src/polymarket_arb/config.py`
- Modify: `src/polymarket_arb/domain/models.py`
- Modify: `tests/unit/test_config.py`
- Create: `tests/unit/research/test_event_execution_models.py`

- [ ] **Step 1: Write the failing config test**

```python
def test_load_settings_reads_event_execution_controls(tmp_path: Path) -> None:
    config_path = tmp_path / "event_execution.yaml"
    config_path.write_text(
        dedent(
            """
            venue: polymarket
            api:
              gamma_base_url: https://gamma-api.polymarket.com
              clob_base_url: https://clob.polymarket.com
              poll_interval_ms: 500
            event_research:
              candidate_market_limit: 200
              source_registry_path: configs/source_registry.sample.yaml
              response_window_seconds: 120
              max_signal_age_seconds: 15
              min_expected_edge_bps: 25
              default_exit_mode: repricing_target
              repricing_target_bps: 50
              max_holding_seconds: 900
              exit_slippage_buffer: 0.01
              allow_hold_to_resolution: true
            markets:
              - slug: market-one
                max_capital_usd: 50
            strategy:
              raw_alert_threshold: 0.99
              fee_rate: 0.0
              slippage_buffer: 0.0
              operational_buffer: 0.0
              stale_after_ms: 5000
            portfolio:
              starting_cash_usd: 500
              max_total_deployed_usd: 200
            """
        ).strip()
    )

    settings = load_settings(config_path)

    assert settings.event_research.repricing_target_bps == 50
    assert settings.event_research.allow_hold_to_resolution is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src .venv/bin/pytest tests/unit/test_config.py::test_load_settings_reads_event_execution_controls -v`
Expected: FAIL because the extra execution fields are not in `EventResearchSettings`.

- [ ] **Step 3: Extend `EventResearchSettings` with Phase 2.4 fields**

```python
class EventResearchSettings(BaseModel):
    ...
    repricing_target_bps: float = Field(ge=0, default=50)
    max_holding_seconds: int = Field(gt=0, default=900)
    exit_slippage_buffer: float = Field(ge=0, lt=1, default=0.01)
    allow_hold_to_resolution: bool = False
```

- [ ] **Step 4: Write the failing event-execution model test**

```python
from polymarket_arb.domain.models import DirectionalFillRecord, EventPaperRejectionRecord


def test_directional_fill_record_tracks_vwap_and_exit_mode() -> None:
    fill = DirectionalFillRecord(
        market_id="123",
        direction="YES",
        requested_size=10,
        filled_size=8,
        average_price=0.43125,
        status="partial_fill",
        exit_mode="repricing_target",
    )

    assert fill.status == "partial_fill"
    assert fill.exit_mode == "repricing_target"
```

- [ ] **Step 5: Add structured fill, exit, rejection, and open-position records**

```python
class DirectionalFillRecord(BaseModel):
    market_id: str
    direction: str
    requested_size: float
    filled_size: float
    average_price: float
    status: str
    exit_mode: str


class EventPaperRejectionRecord(BaseModel):
    market_id: str
    slug: str
    timestamp_ms: int
    reason: str
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `PYTHONPATH=src .venv/bin/pytest tests/unit/test_config.py tests/unit/research/test_event_execution_models.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add src/polymarket_arb/config.py src/polymarket_arb/domain/models.py tests/unit/test_config.py tests/unit/research/test_event_execution_models.py
git commit -m "feat: add phase 2.4 execution settings and records"
```

## Task 2: Add Depth-Aware Directional Fill Simulation

**Files:**
- Create: `src/polymarket_arb/sim/directional.py`
- Create: `tests/unit/sim/test_directional_execution.py`

- [ ] **Step 1: Write the failing directional-fill test**

```python
from polymarket_arb.domain.models import BookLevel
from polymarket_arb.sim.directional import simulate_directional_fill


def test_simulate_directional_fill_returns_vwap_for_multi_level_buy() -> None:
    fill = simulate_directional_fill(
        side="buy",
        book_levels=[
            BookLevel(price=0.43, size=5),
            BookLevel(price=0.44, size=5),
        ],
        requested_size=8,
        slippage_buffer=0.0,
    )

    assert fill.status == "filled"
    assert fill.filled_size == 8
    assert round(fill.average_price, 4) == 0.4338
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src .venv/bin/pytest tests/unit/sim/test_directional_execution.py::test_simulate_directional_fill_returns_vwap_for_multi_level_buy -v`
Expected: FAIL because `sim/directional.py` does not exist.

- [ ] **Step 3: Add minimal directional fill simulation**

```python
def simulate_directional_fill(
    *,
    side: str,
    book_levels: list[BookLevel],
    requested_size: float,
    slippage_buffer: float,
) -> DirectionalFillRecord:
    ...
```

- [ ] **Step 4: Write the failing partial-exit test**

```python
def test_simulate_directional_fill_marks_partial_fill_when_depth_runs_out() -> None:
    fill = simulate_directional_fill(
        side="sell",
        book_levels=[BookLevel(price=0.58, size=3)],
        requested_size=5,
        slippage_buffer=0.0,
    )

    assert fill.status == "partial_fill"
    assert fill.filled_size == 3
```

- [ ] **Step 5: Add partial-fill and no-liquidity classification**

```python
if filled_size == 0:
    status = "no_fill"
elif filled_size < requested_size:
    status = "partial_fill"
else:
    status = "filled"
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `PYTHONPATH=src .venv/bin/pytest tests/unit/sim/test_directional_execution.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add src/polymarket_arb/sim/directional.py tests/unit/sim/test_directional_execution.py
git commit -m "feat: add directional fill simulation"
```

## Task 3: Make The Directional Ledger Lot-Aware

**Files:**
- Modify: `src/polymarket_arb/portfolio/directional.py`
- Modify: `tests/unit/portfolio/test_directional_ledger.py`

- [ ] **Step 1: Write the failing partial-exit ledger test**

```python
def test_directional_ledger_supports_partial_exit() -> None:
    ledger = DirectionalLedger(starting_cash_usd=500)
    trade_id = ledger.open_position(
        market_id="123",
        direction="YES",
        size=10,
        entry_price=0.42,
    )

    ledger.close_position(trade_id=trade_id, exit_price=0.58, close_size=4)

    assert ledger.realized_pnl_usd == 0.64
    assert ledger.open_positions()[0].size == 6
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src .venv/bin/pytest tests/unit/portfolio/test_directional_ledger.py::test_directional_ledger_supports_partial_exit -v`
Expected: FAIL because `close_position` does not take `close_size` and open positions are not exposed.

- [ ] **Step 3: Add partial-close support and open-position snapshots**

```python
def close_position(self, *, trade_id: str, exit_price: float, close_size: float | None = None) -> None:
    ...

def open_positions(self) -> list[DirectionalPosition]:
    return list(self._positions.values())
```

- [ ] **Step 4: Write the failing deployment-and-cost-basis test**

```python
def test_directional_ledger_tracks_remaining_cost_basis_after_partial_exit() -> None:
    ledger = DirectionalLedger(starting_cash_usd=500)
    trade_id = ledger.open_position(
        market_id="123",
        direction="YES",
        size=10,
        entry_price=0.42,
    )

    ledger.close_position(trade_id=trade_id, exit_price=0.50, close_size=5)

    assert ledger.deployed_cost_basis_usd == 2.1
```

- [ ] **Step 5: Keep cost basis proportional on partial exits**

```python
remaining_size = position.size - close_size
remaining_cost_basis = position.entry_price * remaining_size
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `PYTHONPATH=src .venv/bin/pytest tests/unit/portfolio/test_directional_ledger.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add src/polymarket_arb/portfolio/directional.py tests/unit/portfolio/test_directional_ledger.py
git commit -m "feat: add lot-aware directional ledger"
```

## Task 4: Add Exit Policy And Hold-To-Resolution Lifecycle Logic

**Files:**
- Create: `src/polymarket_arb/portfolio/event_lifecycle.py`
- Create: `tests/unit/portfolio/test_event_lifecycle.py`

- [ ] **Step 1: Write the failing repricing-target test**

```python
from polymarket_arb.portfolio.event_lifecycle import decide_exit_action


def test_decide_exit_action_triggers_repricing_target() -> None:
    action = decide_exit_action(
        exit_mode="repricing_target",
        entry_price=0.42,
        current_price=0.48,
        repricing_target_bps=50,
        elapsed_seconds=30,
        max_holding_seconds=900,
        terminal_signal=False,
        allow_hold_to_resolution=False,
    )

    assert action == "exit_now"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src .venv/bin/pytest tests/unit/portfolio/test_event_lifecycle.py::test_decide_exit_action_triggers_repricing_target -v`
Expected: FAIL because `event_lifecycle.py` does not exist.

- [ ] **Step 3: Add the lifecycle decision helper**

```python
def decide_exit_action(
    *,
    exit_mode: str,
    entry_price: float,
    current_price: float,
    repricing_target_bps: float,
    elapsed_seconds: int,
    max_holding_seconds: int,
    terminal_signal: bool,
    allow_hold_to_resolution: bool,
) -> str:
    ...
```

- [ ] **Step 4: Write the failing hold-to-resolution test**

```python
def test_decide_exit_action_holds_terminal_signal_to_resolution() -> None:
    action = decide_exit_action(
        exit_mode="hold_to_resolution",
        entry_price=0.42,
        current_price=0.60,
        repricing_target_bps=50,
        elapsed_seconds=600,
        max_holding_seconds=900,
        terminal_signal=True,
        allow_hold_to_resolution=True,
    )

    assert action == "hold_to_resolution"
```

- [ ] **Step 5: Add time-stop and hold-to-resolution cases**

```python
if exit_mode == "hold_to_resolution" and terminal_signal and allow_hold_to_resolution:
    return "hold_to_resolution"
if elapsed_seconds >= max_holding_seconds:
    return "exit_now"
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `PYTHONPATH=src .venv/bin/pytest tests/unit/portfolio/test_event_lifecycle.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add src/polymarket_arb/portfolio/event_lifecycle.py tests/unit/portfolio/test_event_lifecycle.py
git commit -m "feat: add event exit lifecycle rules"
```

## Task 5: Integrate Realistic Fills And Lifecycle Into `EventPaperRunner`

**Files:**
- Modify: `src/polymarket_arb/research/event_paper.py`
- Modify: `tests/unit/research/test_event_paper.py`

- [ ] **Step 1: Write the failing event-paper partial-fill test**

```python
def test_event_paper_runner_rejects_unfilled_entry() -> None:
    runner = EventPaperRunner(
        starting_cash_usd=500,
        max_total_deployed_usd=200,
        default_exit_mode="repricing_target",
    )

    result = runner.on_signal(
        market_id="123",
        slug="will-example-happen",
        direction="YES",
        expected_edge_bps=40,
        asks=[],
        bids=[],
        timestamp_ms=1_700_000_000_000,
    )

    assert result.decision == "reject"
    assert result.reason == "entry_no_fill"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src .venv/bin/pytest tests/unit/research/test_event_paper.py::test_event_paper_runner_rejects_unfilled_entry -v`
Expected: FAIL because `EventPaperRunner` still uses `best_ask` and `available_size`.

- [ ] **Step 3: Replace best-ask placeholders with ladder-based fills**

```python
entry_fill = simulate_directional_fill(
    side="buy",
    book_levels=asks,
    requested_size=requested_size,
    slippage_buffer=self.entry_slippage_buffer,
)
```

- [ ] **Step 4: Write the failing lifecycle-outcome test**

```python
def test_event_paper_runner_records_open_position_when_exit_not_triggered() -> None:
    runner = EventPaperRunner(
        starting_cash_usd=500,
        max_total_deployed_usd=200,
        default_exit_mode="repricing_target",
    )

    outcome = runner.evaluate_open_position(
        trade_id="trade-1",
        market_id="123",
        bids=[BookLevel(price=0.45, size=10)],
        current_timestamp_ms=1_700_000_030_000,
        terminal_signal=False,
    )

    assert outcome.decision == "hold"
```

- [ ] **Step 5: Add exit evaluation, rejection logging, and open-position snapshots**

```python
class EventPaperRunner:
    ...
    self.rejection_log: list[EventPaperRejectionRecord] = []
    self.exit_log: list[DirectionalFillRecord] = []

    def evaluate_open_position(... ) -> EventPaperOutcome:
        ...
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `PYTHONPATH=src .venv/bin/pytest tests/unit/research/test_event_paper.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add src/polymarket_arb/research/event_paper.py tests/unit/research/test_event_paper.py
git commit -m "feat: add realistic event paper lifecycle"
```

## Task 6: Expose Richer Artifacts Through CLI And Writers

**Files:**
- Modify: `src/polymarket_arb/reporting/writers.py`
- Modify: `src/polymarket_arb/cli.py`
- Modify: `README.md`
- Modify: `tests/integration/test_run_event_paper_cli.py`

- [ ] **Step 1: Write the failing CLI artifact test**

```python
def test_run_event_paper_writes_rejections_exits_and_open_positions(tmp_path: Path, monkeypatch) -> None:
    result = runner.invoke(
        app,
        [
            "run-event-paper",
            "--config-path",
            str(config_path),
            "--output-dir",
            str(output_dir),
        ],
    )

    assert result.exit_code == 0
    assert (output_dir / "rejections.json").exists()
    assert (output_dir / "exit_log.json").exists()
    assert (output_dir / "open_positions.json").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src .venv/bin/pytest tests/integration/test_run_event_paper_cli.py::test_run_event_paper_writes_rejections_exits_and_open_positions -v`
Expected: FAIL because the CLI only writes `summary.json` and `trade_log.json`.

- [ ] **Step 3: Add writer helpers for new artifacts**

```python
def write_rejection_log(output_dir: Path, payload: Any) -> Path:
    ...


def write_exit_log(output_dir: Path, payload: Any) -> Path:
    ...


def write_open_positions(output_dir: Path, payload: Any) -> Path:
    ...
```

- [ ] **Step 4: Extend `run-event-paper` to write the richer artifact set**

```python
write_trade_log(output_dir, runner.trade_log)
write_rejection_log(output_dir, runner.rejection_log)
write_exit_log(output_dir, runner.exit_log)
write_open_positions(output_dir, runner.ledger.open_positions())
```

- [ ] **Step 5: Document the richer Phase 2.4 workflow in `README.md`**

```markdown
- `trade_log.json`: accepted entries with realized fill pricing
- `rejections.json`: rejected entries with reason codes
- `exit_log.json`: realized exits and exit-mode outcomes
- `open_positions.json`: remaining exposure after the run
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `PYTHONPATH=src .venv/bin/pytest tests/integration/test_run_event_paper_cli.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add src/polymarket_arb/reporting/writers.py src/polymarket_arb/cli.py README.md tests/integration/test_run_event_paper_cli.py
git commit -m "feat: expose phase 2.4 event paper artifacts"
```

## Task 7: Full Verification

**Files:**
- Verify: `src/polymarket_arb/...`
- Verify: `tests/...`
- Verify: `README.md`

- [ ] **Step 1: Run the Phase 2.4-focused unit suite**

Run: `PYTHONPATH=src .venv/bin/pytest tests/unit/test_config.py tests/unit/research/test_event_execution_models.py tests/unit/sim/test_directional_execution.py tests/unit/portfolio/test_directional_ledger.py tests/unit/portfolio/test_event_lifecycle.py tests/unit/research/test_event_paper.py -v`
Expected: PASS

- [ ] **Step 2: Run the event-paper integration suite**

Run: `PYTHONPATH=src .venv/bin/pytest tests/integration/test_run_event_paper_cli.py -v`
Expected: PASS

- [ ] **Step 3: Run the full repo suite to guard against regressions**

Run: `PYTHONPATH=src .venv/bin/pytest -v`
Expected: PASS

- [ ] **Step 4: Commit any final docs or fixture cleanups**

```bash
git add README.md tests/integration/test_run_event_paper_cli.py
git commit -m "docs: finalize phase 2.4 execution workflow"
```

## Notes For Execution

- Keep Phase 2.4 scoped to honesty, not sophistication. A simple but truthful exit model is better than a large policy engine with vague assumptions.
- Do not let `EventPaperRunner` grow into a giant all-in-one module. Push fill logic and lifecycle decisions into focused helpers as the plan says.
- Preserve the existing Phase 2.3 artifact shape where possible, then add new files rather than silently changing old semantics.
- If partial exits and hold-to-resolution accounting expose deeper inconsistencies in the current directional model, stop and simplify before moving toward Phase 3.
