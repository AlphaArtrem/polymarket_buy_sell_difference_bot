# Polymarket Phase 6 Authenticated Execution And Safety Rails Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add authenticated Polymarket execution behind strict safety rails so the bot can place tiny real orders only after replay and paper evidence justify it.

**Architecture:** Keep the engine and public-data adapters independent from signing and order submission. Introduce a dedicated execution boundary with wallet configuration, preflight checks, order preview, safety policy enforcement, and auditable submission logs. Use the official execution SDK only at the authenticated edge if it materially reduces signing risk.

**Tech Stack:** Python 3.9+, `httpx`, `pydantic`, `typer`, `pytest`; optionally `py-clob-client` only for authenticated trading edge

---

## Scope Check

This plan intentionally covers:

- wallet and API credential config
- preflight account checks
- order preview and dry-run mode
- real taker order submission with small-size guardrails
- audit logging and kill switches

This plan does not include:

- unattended high-frequency deployment
- maker-order strategy
- multi-venue routing

## File Structure

### Files To Modify

- Modify: `src/polymarket_arb/config.py`
  Add wallet and execution settings.
- Modify: `src/polymarket_arb/cli.py`
  Add authenticated preflight and live execution commands.
- Modify: `README.md`
  Document credential loading and safety warnings.

### Files To Create

- Create: `src/polymarket_arb/execution/__init__.py`
  Package marker.
- Create: `src/polymarket_arb/execution/client.py`
  Thin authenticated client wrapper.
- Create: `src/polymarket_arb/execution/preflight.py`
  Balance, allowance, and market-readiness checks.
- Create: `src/polymarket_arb/execution/policy.py`
  Safety-rail evaluation before any live submission.
- Create: `src/polymarket_arb/execution/router.py`
  Executes paired taker orders using the authenticated client.
- Create: `src/polymarket_arb/execution/audit.py`
  Writes immutable local order-attempt logs.
- Create: `tests/unit/execution/test_preflight.py`
  Tests for balance and allowance checks.
- Create: `tests/unit/execution/test_policy.py`
  Tests for safety policy enforcement.
- Create: `tests/unit/execution/test_router.py`
  Tests for paired order routing and abort rules.
- Create: `tests/integration/test_execution_cli.py`
  CLI test for preflight and dry-run live execution.

## Task 1: Add Execution And Wallet Config Models

**Files:**
- Modify: `src/polymarket_arb/config.py`
- Create: `tests/unit/execution/test_policy.py`

- [ ] **Step 1: Write the failing config test**

```python
from pathlib import Path

from polymarket_arb.config import load_settings


def test_load_settings_reads_execution_safety_limits(tmp_path: Path) -> None:
    config_path = tmp_path / "live.yaml"
    config_path.write_text(
        """
        venue: polymarket
        api:
          gamma_base_url: https://gamma-api.polymarket.com
          clob_base_url: https://clob.polymarket.com
          poll_interval_ms: 500
        execution:
          enabled: false
          max_order_notional_usd: 10
          require_manual_confirmation: true
        wallet:
          chain_id: 137
          funder_address: 0xabc
        markets:
          - slug: bitboy-convicted
            max_capital_usd: 10
        strategy:
          raw_alert_threshold: 0.99
          fee_rate: 0.01
          slippage_buffer: 0.005
          operational_buffer: 0.005
          stale_after_ms: 5000
        portfolio:
          starting_cash_usd: 100
          max_total_deployed_usd: 50
        """.strip()
    )

    settings = load_settings(config_path)

    assert settings.execution.max_order_notional_usd == 10
    assert settings.wallet.chain_id == 137
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src .venv/bin/pytest tests/unit/execution/test_policy.py -v`
Expected: FAIL because wallet and execution sections do not exist.

- [ ] **Step 3: Add minimal config models**

```python
class ExecutionSettings(BaseModel):
    enabled: bool = False
    max_order_notional_usd: float = Field(gt=0)
    require_manual_confirmation: bool = True
    dry_run: bool = True


class WalletSettings(BaseModel):
    chain_id: int
    funder_address: str
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src .venv/bin/pytest tests/unit/execution/test_policy.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/polymarket_arb/config.py tests/unit/execution/test_policy.py
git commit -m "feat: add execution config models"
```

## Task 2: Implement Preflight Checks

**Files:**
- Create: `src/polymarket_arb/execution/client.py`
- Create: `src/polymarket_arb/execution/preflight.py`
- Create: `tests/unit/execution/test_preflight.py`

- [ ] **Step 1: Write the failing preflight test**

```python
from polymarket_arb.execution.preflight import run_preflight


def test_run_preflight_fails_when_free_collateral_is_below_minimum() -> None:
    report = run_preflight(
        balances={"usdc": 4.0},
        min_required_usd=10.0,
        allowances={"exchange": 100.0},
    )

    assert report.ok is False
    assert "insufficient_usdc" in report.failures
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src .venv/bin/pytest tests/unit/execution/test_preflight.py -v`
Expected: FAIL because preflight logic does not exist.

- [ ] **Step 3: Add thin authenticated client interface**

```python
class AuthenticatedExecutionClient(Protocol):
    def get_balances(self) -> dict[str, float]: ...
    def get_allowances(self) -> dict[str, float]: ...
```

- [ ] **Step 4: Implement preflight report generation**

```python
def run_preflight(
    *, balances: dict[str, float], allowances: dict[str, float], min_required_usd: float
) -> PreflightReport:
    failures = []
    if balances.get("usdc", 0.0) < min_required_usd:
        failures.append("insufficient_usdc")
    if allowances.get("exchange", 0.0) < min_required_usd:
        failures.append("insufficient_allowance")
    return PreflightReport(ok=not failures, failures=failures)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `PYTHONPATH=src .venv/bin/pytest tests/unit/execution/test_preflight.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/polymarket_arb/execution/client.py src/polymarket_arb/execution/preflight.py tests/unit/execution/test_preflight.py
git commit -m "feat: add execution preflight checks"
```

## Task 3: Add Safety Policy And Order Preview

**Files:**
- Create: `src/polymarket_arb/execution/policy.py`
- Create: `src/polymarket_arb/execution/audit.py`
- Create: `tests/unit/execution/test_policy.py`

- [ ] **Step 1: Write the failing safety-policy test**

```python
from polymarket_arb.execution.policy import evaluate_live_trade_policy


def test_evaluate_live_trade_policy_blocks_orders_above_phase_limit() -> None:
    decision = evaluate_live_trade_policy(
        estimated_notional_usd=25.0,
        max_order_notional_usd=10.0,
        market_slug="bitboy-convicted",
        dry_run=False,
    )

    assert decision.allowed is False
    assert decision.reason == "max_order_notional_exceeded"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src .venv/bin/pytest tests/unit/execution/test_policy.py -v`
Expected: FAIL because no live trade policy exists.

- [ ] **Step 3: Add explicit policy result models**

```python
class LiveTradePolicyDecision(BaseModel):
    allowed: bool
    reason: str | None = None
```

- [ ] **Step 4: Add audit record writer**

```python
def append_audit_record(output_path: Path, record: dict[str, Any]) -> None:
    ...
```

- [ ] **Step 5: Run test to verify it passes**

Run: `PYTHONPATH=src .venv/bin/pytest tests/unit/execution/test_policy.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/polymarket_arb/execution/policy.py src/polymarket_arb/execution/audit.py tests/unit/execution/test_policy.py
git commit -m "feat: add live trade safety policy"
```

## Task 4: Implement Paired Taker Router With Dry-Run First

**Files:**
- Create: `src/polymarket_arb/execution/router.py`
- Modify: `src/polymarket_arb/cli.py`
- Create: `tests/unit/execution/test_router.py`
- Create: `tests/integration/test_execution_cli.py`

- [ ] **Step 1: Write the failing router test**

```python
from polymarket_arb.execution.router import route_pair_order


def test_route_pair_order_returns_preview_in_dry_run_mode() -> None:
    result = route_pair_order(
        market_id="market-1",
        yes_token_id="yes",
        no_token_id="no",
        pair_size=5,
        dry_run=True,
    )

    assert result.status == "preview"
    assert result.submitted_orders == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src .venv/bin/pytest tests/unit/execution/test_router.py tests/integration/test_execution_cli.py -v`
Expected: FAIL because routing logic and CLI commands do not exist.

- [ ] **Step 3: Add router skeleton**

```python
def route_pair_order(... ) -> RouteResult:
    if dry_run:
        return RouteResult(status="preview", submitted_orders=[])
    ...
```

- [ ] **Step 4: Add CLI commands**

```python
@app.command("live-preflight")
def live_preflight(...):
    ...


@app.command("run-live")
def run_live(...):
    ...
```

- [ ] **Step 5: Make dry-run the default and require explicit enablement**

```python
if not settings.execution.enabled:
    raise typer.Exit(code=1)
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `PYTHONPATH=src .venv/bin/pytest tests/unit/execution/test_router.py tests/integration/test_execution_cli.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add src/polymarket_arb/execution/router.py src/polymarket_arb/cli.py tests/unit/execution/test_router.py tests/integration/test_execution_cli.py
git commit -m "feat: add authenticated execution router"
```

## Task 5: Verify The Full Phase

- [ ] **Step 1: Document credential and safety requirements**

```markdown
Live execution is opt-in, dry-run by default, and should only be used with tiny notional caps.
```

- [ ] **Step 2: Run focused verification**

Run: `PYTHONPATH=src .venv/bin/pytest tests/unit/execution tests/integration/test_execution_cli.py -v`
Expected: PASS

- [ ] **Step 3: Run the full suite**

Run: `PYTHONPATH=src .venv/bin/pytest -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs: add authenticated execution workflow"
```
