# Polymarket Phase 5 Research Sweeps And Market Selection Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a repeatable research harness that can replay many captured sessions, sweep strategy parameters, and rank markets by executable full-set opportunity quality.

**Architecture:** Keep the trading engine as the source of truth, but add a research layer around it: experiment configs, batch replay orchestration, metric aggregation, and market-level ranking reports. This phase is about evidence and selection discipline, not live execution.

**Tech Stack:** Python 3.9+, `typer`, `PyYAML`, `pydantic`, `pytest`, JSON/CSV outputs

---

## Scope Check

This plan intentionally covers:

- experiment config files
- parameter sweep orchestration
- replay batch metrics
- market ranking and allowlist curation outputs

This plan does not include:

- live order placement
- online learning
- automated market discovery across the entire venue

## File Structure

### Files To Modify

- Modify: `src/polymarket_arb/config.py`
  Add experiment config models and replay-batch settings.
- Modify: `src/polymarket_arb/cli.py`
  Add research CLI commands.
- Modify: `src/polymarket_arb/reporting/writers.py`
  Add helpers for batch metrics and ranking reports.
- Modify: `README.md`
  Document sweep usage.

### Files To Create

- Create: `configs/research.sample.yaml`
  Sample sweep configuration.
- Create: `src/polymarket_arb/research/__init__.py`
  Package marker.
- Create: `src/polymarket_arb/research/runner.py`
  Orchestrates replay batches and parameter sweeps.
- Create: `src/polymarket_arb/research/metrics.py`
  Aggregates run-level and market-level metrics.
- Create: `src/polymarket_arb/research/ranking.py`
  Produces ranked market recommendations.
- Create: `tests/unit/research/test_metrics.py`
  Verify aggregate metric calculations.
- Create: `tests/unit/research/test_ranking.py`
  Verify ranking heuristics.
- Create: `tests/integration/test_research_cli.py`
  End-to-end sweep CLI test using fixture replay runs.

## Task 1: Add Experiment Config Models

**Files:**
- Modify: `src/polymarket_arb/config.py`
- Create: `configs/research.sample.yaml`
- Create: `tests/unit/research/test_metrics.py`

- [ ] **Step 1: Write the failing config test**

```python
from pathlib import Path

from polymarket_arb.config import load_research_settings


def test_load_research_settings_reads_threshold_grid(tmp_path: Path) -> None:
    config_path = tmp_path / "research.yaml"
    config_path.write_text(
        """
        runs:
          - run_dir: artifacts/capture-a
        parameter_grid:
          raw_alert_threshold: [0.985, 0.99]
          operational_buffer: [0.002, 0.005]
        """.strip()
    )

    settings = load_research_settings(config_path)

    assert settings.parameter_grid.raw_alert_threshold == [0.985, 0.99]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src .venv/bin/pytest tests/unit/research/test_metrics.py -v`
Expected: FAIL because research settings do not exist.

- [ ] **Step 3: Add minimal research config models**

```python
class ResearchRunSelection(BaseModel):
    run_dir: str


class ParameterGrid(BaseModel):
    raw_alert_threshold: list[float]
    operational_buffer: list[float]
```

- [ ] **Step 4: Add sample config**

```yaml
runs:
  - run_dir: artifacts/live-smoke-run
parameter_grid:
  raw_alert_threshold: [0.985, 0.99]
  operational_buffer: [0.002, 0.005]
```

- [ ] **Step 5: Run test to verify it passes**

Run: `PYTHONPATH=src .venv/bin/pytest tests/unit/research/test_metrics.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/polymarket_arb/config.py configs/research.sample.yaml tests/unit/research/test_metrics.py
git commit -m "feat: add research config models"
```

## Task 2: Build Replay Batch Runner And Aggregate Metrics

**Files:**
- Create: `src/polymarket_arb/research/runner.py`
- Create: `src/polymarket_arb/research/metrics.py`
- Create: `tests/unit/research/test_metrics.py`

- [ ] **Step 1: Write the failing aggregate-metrics test**

```python
from polymarket_arb.research.metrics import aggregate_run_metrics


def test_aggregate_run_metrics_computes_trade_rate_and_edge() -> None:
    result = aggregate_run_metrics(
        [
            {"trades": 2, "rejections": 8, "realized_pnl_usd": 0.2},
            {"trades": 1, "rejections": 9, "realized_pnl_usd": 0.1},
        ]
    )

    assert result.total_trades == 3
    assert result.trade_rate == 0.15
    assert result.total_realized_pnl_usd == 0.3
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src .venv/bin/pytest tests/unit/research/test_metrics.py -v`
Expected: FAIL because research metrics do not exist.

- [ ] **Step 3: Add minimal runner and metrics helpers**

```python
def aggregate_run_metrics(summaries: list[dict[str, float]]) -> AggregateMetrics:
    ...


def run_replay_batch(run_dirs: list[Path], parameter_sets: list[dict[str, float]]) -> list[BatchResult]:
    ...
```

- [ ] **Step 4: Keep the runner thin**

```python
for run_dir in run_dirs:
    for params in parameter_sets:
        summary = replay_once(run_dir=run_dir, overrides=params)
        results.append(...)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `PYTHONPATH=src .venv/bin/pytest tests/unit/research/test_metrics.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/polymarket_arb/research/runner.py src/polymarket_arb/research/metrics.py tests/unit/research/test_metrics.py
git commit -m "feat: add replay batch metrics"
```

## Task 3: Rank Markets And Recommend Allowlist Changes

**Files:**
- Create: `src/polymarket_arb/research/ranking.py`
- Create: `tests/unit/research/test_ranking.py`

- [ ] **Step 1: Write the failing ranking test**

```python
from polymarket_arb.research.ranking import rank_markets


def test_rank_markets_prefers_repeatable_positive_pnl_and_low_broken_pair_rate() -> None:
    ranked = rank_markets(
        [
            {"slug": "a", "realized_pnl_usd": 1.2, "broken_pair_rate": 0.01},
            {"slug": "b", "realized_pnl_usd": 1.5, "broken_pair_rate": 0.30},
        ]
    )

    assert ranked[0].slug == "a"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src .venv/bin/pytest tests/unit/research/test_ranking.py -v`
Expected: FAIL because market ranking does not exist.

- [ ] **Step 3: Add minimal ranking model and function**

```python
def rank_markets(rows: list[dict[str, float]]) -> list[MarketRanking]:
    score = realized_pnl_usd - broken_pair_rate_penalty
    ...
```

- [ ] **Step 4: Keep the ranking heuristic explicit and simple**

```python
score = row["realized_pnl_usd"] - (row["broken_pair_rate"] * 5.0)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `PYTHONPATH=src .venv/bin/pytest tests/unit/research/test_ranking.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/polymarket_arb/research/ranking.py tests/unit/research/test_ranking.py
git commit -m "feat: add market ranking heuristics"
```

## Task 4: Add CLI Commands For Sweeps And Ranking Reports

**Files:**
- Modify: `src/polymarket_arb/cli.py`
- Modify: `src/polymarket_arb/reporting/writers.py`
- Modify: `README.md`
- Create: `tests/integration/test_research_cli.py`

- [ ] **Step 1: Write the failing CLI test**

```python
from typer.testing import CliRunner

from polymarket_arb.cli import app


def test_run_research_sweep_writes_batch_reports(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["run-research", "--config-path", "configs/research.sample.yaml", "--output-dir", str(tmp_path)],
    )

    assert result.exit_code == 0
    assert (tmp_path / "batch_summary.json").exists()
    assert (tmp_path / "market_rankings.json").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src .venv/bin/pytest tests/integration/test_research_cli.py -v`
Expected: FAIL because no research CLI exists.

- [ ] **Step 3: Add CLI entrypoints**

```python
@app.command("run-research")
def run_research(...):
    ...
```

- [ ] **Step 4: Add report writers**

```python
write_json(output_dir / "batch_summary.json", summary.model_dump())
write_json(output_dir / "market_rankings.json", [row.model_dump() for row in ranked])
```

- [ ] **Step 5: Document usage**

```markdown
PYTHONPATH=src .venv/bin/python -m polymarket_arb.cli run-research --config-path configs/research.sample.yaml --output-dir artifacts/research
```

- [ ] **Step 6: Run test to verify it passes**

Run: `PYTHONPATH=src .venv/bin/pytest tests/integration/test_research_cli.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add src/polymarket_arb/cli.py src/polymarket_arb/reporting/writers.py README.md tests/integration/test_research_cli.py
git commit -m "feat: add research sweep cli"
```

## Task 5: Verify The Full Phase

- [ ] **Step 1: Run focused verification**

Run: `PYTHONPATH=src .venv/bin/pytest tests/unit/research tests/integration/test_research_cli.py -v`
Expected: PASS

- [ ] **Step 2: Run the full suite**

Run: `PYTHONPATH=src .venv/bin/pytest -v`
Expected: PASS

- [ ] **Step 3: Commit any final docs cleanup**

```bash
git add README.md configs/research.sample.yaml
git commit -m "docs: add research sweep workflow"
```
