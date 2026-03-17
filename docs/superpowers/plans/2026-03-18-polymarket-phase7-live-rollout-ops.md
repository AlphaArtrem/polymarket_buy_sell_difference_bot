# Polymarket Phase 7 Live Rollout And Runtime Operations Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Operationalize tiny-size live trading with runtime persistence, monitoring, resolution workflows, and an explicit capital ladder from learning size to meaningful but still bounded deployment.

**Architecture:** Keep trading decisions inside the existing engine and execution boundary, but wrap them with runtime state, monitoring, operator controls, and post-trade workflows. This phase is about staying safe in production, not adding more strategy ideas.

**Tech Stack:** Python 3.9+, `typer`, `sqlite3` or file-backed JSON state, `pytest`

---

## Scope Check

This plan intentionally covers:

- runtime state persistence
- resume-safe live sessions
- operator dashboards and alerts
- resolution and merge workflow support
- staged capital ladder controls

This plan does not include:

- multi-server deployment
- autonomous market discovery
- high-frequency latency engineering

## File Structure

### Files To Modify

- Modify: `src/polymarket_arb/config.py`
  Add runtime and capital-ladder settings.
- Modify: `src/polymarket_arb/cli.py`
  Add operator commands for status, resume, and resolution workflows.
- Modify: `README.md`
  Add runbook-style commands and rollout guidance.

### Files To Create

- Create: `src/polymarket_arb/runtime/__init__.py`
  Package marker.
- Create: `src/polymarket_arb/runtime/state.py`
  Persist live session state, open lots, and audit checkpoints.
- Create: `src/polymarket_arb/runtime/monitoring.py`
  Generate health summaries and alertable conditions.
- Create: `src/polymarket_arb/runtime/ladder.py`
  Enforce staged capital progression.
- Create: `src/polymarket_arb/runtime/resolution.py`
  Helper functions for lot resolution and merge tracking.
- Create: `tests/unit/runtime/test_state.py`
  Tests for runtime persistence and resume.
- Create: `tests/unit/runtime/test_monitoring.py`
  Tests for alert generation.
- Create: `tests/unit/runtime/test_ladder.py`
  Tests for capital-ladder enforcement.
- Create: `tests/integration/test_runtime_cli.py`
  CLI tests for status, resume, and resolution commands.

## Task 1: Add Runtime And Capital-Ladder Config

**Files:**
- Modify: `src/polymarket_arb/config.py`
- Create: `tests/unit/runtime/test_ladder.py`

- [ ] **Step 1: Write the failing config test**

```python
from pathlib import Path

from polymarket_arb.config import load_settings


def test_load_settings_reads_runtime_ladder_limits(tmp_path: Path) -> None:
    config_path = tmp_path / "runtime.yaml"
    config_path.write_text(
        """
        venue: polymarket
        api:
          gamma_base_url: https://gamma-api.polymarket.com
          clob_base_url: https://clob.polymarket.com
          poll_interval_ms: 500
        markets:
          - slug: bitboy-convicted
            max_capital_usd: 50
        strategy:
          raw_alert_threshold: 0.99
          fee_rate: 0.01
          slippage_buffer: 0.005
          operational_buffer: 0.005
          stale_after_ms: 5000
        portfolio:
          starting_cash_usd: 100
          max_total_deployed_usd: 50
        runtime:
          state_path: artifacts/runtime/state.json
          alert_stale_after_seconds: 30
        ladder:
          stages: [100, 500, 1000]
          require_positive_sessions: 5
        """.strip()
    )

    settings = load_settings(config_path)

    assert settings.ladder.stages == [100, 500, 1000]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src .venv/bin/pytest tests/unit/runtime/test_ladder.py -v`
Expected: FAIL because runtime and ladder settings do not exist.

- [ ] **Step 3: Add minimal runtime config models**

```python
class RuntimeSettings(BaseModel):
    state_path: str
    alert_stale_after_seconds: int = Field(gt=0)


class LadderSettings(BaseModel):
    stages: list[float]
    require_positive_sessions: int = Field(ge=1)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src .venv/bin/pytest tests/unit/runtime/test_ladder.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/polymarket_arb/config.py tests/unit/runtime/test_ladder.py
git commit -m "feat: add runtime ladder config"
```

## Task 2: Persist Live Runtime State And Support Resume

**Files:**
- Create: `src/polymarket_arb/runtime/state.py`
- Create: `tests/unit/runtime/test_state.py`

- [ ] **Step 1: Write the failing state test**

```python
from pathlib import Path

from polymarket_arb.runtime.state import RuntimeStateStore


def test_runtime_state_store_round_trips_open_lots(tmp_path: Path) -> None:
    store = RuntimeStateStore(tmp_path / "state.json")
    store.save({"open_lots": [{"lot_id": "lot-1"}]})

    assert store.load()["open_lots"][0]["lot_id"] == "lot-1"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src .venv/bin/pytest tests/unit/runtime/test_state.py -v`
Expected: FAIL because no runtime state store exists.

- [ ] **Step 3: Add minimal file-backed state store**

```python
class RuntimeStateStore:
    def __init__(self, path: Path) -> None:
        self._path = path

    def save(self, payload: dict[str, Any]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    def load(self) -> dict[str, Any]:
        if not self._path.exists():
            return {"session_id": None, "open_lots": [], "last_event_timestamp_ms": 0, "last_order_attempt": None}
        return json.loads(self._path.read_text(encoding="utf-8"))
```

- [ ] **Step 4: Add a resume-safe schema**

```python
{
  "session_id": "...",
  "open_lots": [],
  "last_event_timestamp_ms": 0,
  "last_order_attempt": None
}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `PYTHONPATH=src .venv/bin/pytest tests/unit/runtime/test_state.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/polymarket_arb/runtime/state.py tests/unit/runtime/test_state.py
git commit -m "feat: add runtime state persistence"
```

## Task 3: Add Monitoring And Alert Conditions

**Files:**
- Create: `src/polymarket_arb/runtime/monitoring.py`
- Create: `tests/unit/runtime/test_monitoring.py`

- [ ] **Step 1: Write the failing monitoring test**

```python
from polymarket_arb.runtime.monitoring import evaluate_runtime_health


def test_evaluate_runtime_health_flags_stale_feed_and_open_broken_pairs() -> None:
    report = evaluate_runtime_health(
        seconds_since_last_event=45,
        alert_stale_after_seconds=30,
        broken_pair_count=1,
    )

    assert report.ok is False
    assert "stale_feed" in report.alerts
    assert "broken_pairs_present" in report.alerts
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src .venv/bin/pytest tests/unit/runtime/test_monitoring.py -v`
Expected: FAIL because runtime monitoring does not exist.

- [ ] **Step 3: Add minimal health evaluation**

```python
def evaluate_runtime_health(... ) -> RuntimeHealthReport:
    ...
```

- [ ] **Step 4: Keep alerts explicit and flat**

```python
alerts = []
if seconds_since_last_event > alert_stale_after_seconds:
    alerts.append("stale_feed")
```

- [ ] **Step 5: Run test to verify it passes**

Run: `PYTHONPATH=src .venv/bin/pytest tests/unit/runtime/test_monitoring.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/polymarket_arb/runtime/monitoring.py tests/unit/runtime/test_monitoring.py
git commit -m "feat: add runtime monitoring checks"
```

## Task 4: Add CLI Operator Commands

**Files:**
- Create: `src/polymarket_arb/runtime/ladder.py`
- Create: `src/polymarket_arb/runtime/resolution.py`
- Modify: `src/polymarket_arb/cli.py`
- Create: `tests/integration/test_runtime_cli.py`

- [ ] **Step 1: Write the failing CLI test**

```python
from typer.testing import CliRunner

from polymarket_arb.cli import app


def test_runtime_status_command_reads_persisted_state(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["runtime-status", "--state-path", str(tmp_path / "state.json")])

    assert result.exit_code == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src .venv/bin/pytest tests/integration/test_runtime_cli.py -v`
Expected: FAIL because operator commands do not exist.

- [ ] **Step 3: Add operator CLI commands**

```python
@app.command("runtime-status")
def runtime_status(...):
    ...


@app.command("runtime-resume")
def runtime_resume(...):
    ...


@app.command("resolve-lots")
def resolve_lots(...):
    ...
```

- [ ] **Step 4: Add capital ladder policy**

```python
def next_allowed_stage(stages: list[float], positive_sessions: int, require_positive_sessions: int) -> float:
    ...
```

- [ ] **Step 5: Run test to verify it passes**

Run: `PYTHONPATH=src .venv/bin/pytest tests/integration/test_runtime_cli.py tests/unit/runtime/test_ladder.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/polymarket_arb/runtime/ladder.py src/polymarket_arb/runtime/resolution.py src/polymarket_arb/cli.py tests/integration/test_runtime_cli.py tests/unit/runtime/test_ladder.py
git commit -m "feat: add runtime operator commands"
```

## Task 5: Verify The Full Phase

- [ ] **Step 1: Document the rollout workflow**

```markdown
1. Start at the first ladder stage.
2. Run only with state persistence enabled.
3. Do not advance stages without the configured number of positive sessions.
```

- [ ] **Step 2: Run focused verification**

Run: `PYTHONPATH=src .venv/bin/pytest tests/unit/runtime tests/integration/test_runtime_cli.py -v`
Expected: PASS

- [ ] **Step 3: Run the full suite**

Run: `PYTHONPATH=src .venv/bin/pytest -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs: add runtime rollout workflow"
```
