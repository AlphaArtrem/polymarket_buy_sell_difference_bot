# Polymarket Phase 2.3 Objective-Source Event Research Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a research and paper-trading workflow that finds Polymarket markets with objective external sources, measures source-to-market lag, and ranks one-sided event opportunities.

**Architecture:** Keep the existing Gamma, CLOB, recording, replay, and reporting stack as the foundation. Add a small `sources` package for source registry and source-event normalization, then layer an event-lag tracker and a directional paper runner on top, exposed through dedicated CLI commands. Leave authenticated trading, maker quoting, and cross-market structure logic out of scope.

**Tech Stack:** Python 3.9+, `typer`, `pydantic`, `PyYAML`, `httpx`, `pytest`, JSON artifacts

---

## Scope Check

This plan covers one coherent subsystem: objective-source event research on top of the existing Polymarket tooling. It intentionally does not split execution realism, structural arbitrage, or maker research into separate plans yet.

## File Structure

### Files To Modify

- Modify: `src/polymarket_arb/config.py`
  Add Phase 2.3 settings for market expansion, source registry, lag windows, and event-paper defaults.
- Modify: `src/polymarket_arb/domain/models.py`
  Add enriched market metadata and event-research records.
- Modify: `src/polymarket_arb/clients/gamma.py`
  Add broader market discovery for candidate-market expansion.
- Modify: `src/polymarket_arb/catalog/service.py`
  Build enriched candidate catalogs in addition to the old allowlist path.
- Modify: `src/polymarket_arb/cli.py`
  Add market-expansion, source-lag study, and event-paper commands.
- Modify: `src/polymarket_arb/reporting/writers.py`
  Write new Phase 2.3 artifacts.
- Modify: `README.md`
  Document the Phase 2.3 workflow.
- Modify: `tests/unit/test_config.py`
  Cover new Phase 2.3 config fields.
- Modify: `tests/unit/catalog/test_service.py`
  Cover enriched catalog building.
- Modify: `tests/unit/clients/test_gamma.py`
  Cover broader Gamma market fetches.

### Files To Create

- Create: `configs/event_research.sample.yaml`
  Sample Phase 2.3 config.
- Create: `configs/source_registry.sample.yaml`
  Sample source-registry config.
- Create: `src/polymarket_arb/sources/__init__.py`
  Package marker for source modules.
- Create: `src/polymarket_arb/sources/models.py`
  Source-registry and normalized source-event models.
- Create: `src/polymarket_arb/sources/registry.py`
  Registry loader and validation helpers.
- Create: `src/polymarket_arb/sources/adapters.py`
  Initial source-event normalization helpers.
- Create: `src/polymarket_arb/research/event_lag.py`
  Lead-lag tracker and per-market response summaries.
- Create: `src/polymarket_arb/research/event_ranking.py`
  Ranking helpers for markets and source families.
- Create: `src/polymarket_arb/portfolio/directional.py`
  Directional position ledger for event-paper mode.
- Create: `src/polymarket_arb/research/event_paper.py`
  One-sided paper runner driven by accepted source signals.
- Create: `tests/unit/research/test_event_models.py`
  Verify enriched market and source-event models.
- Create: `tests/unit/sources/test_registry.py`
  Verify registry loading and validation.
- Create: `tests/unit/sources/test_adapters.py`
  Verify source-event normalization.
- Create: `tests/unit/research/test_event_lag.py`
  Verify lag and response-window calculations.
- Create: `tests/unit/research/test_event_ranking.py`
  Verify ranking rules.
- Create: `tests/unit/portfolio/test_directional_ledger.py`
  Verify directional position accounting.
- Create: `tests/unit/research/test_event_paper.py`
  Verify signal acceptance, paper entry, exit, and rejection handling.
- Create: `tests/integration/test_catalog_expand_cli.py`
  End-to-end market-expansion CLI test.
- Create: `tests/integration/test_study_source_lag_cli.py`
  End-to-end lag-study CLI test.
- Create: `tests/integration/test_run_event_paper_cli.py`
  End-to-end event-paper CLI test.
- Create: `tests/fixtures/sources/objective_update.json`
  Source-payload fixture for unit and integration tests.

## Task 1: Add Phase 2.3 Config And Core Models

**Files:**
- Modify: `src/polymarket_arb/config.py`
- Modify: `src/polymarket_arb/domain/models.py`
- Modify: `tests/unit/test_config.py`
- Create: `tests/unit/research/test_event_models.py`
- Create: `configs/event_research.sample.yaml`
- Create: `configs/source_registry.sample.yaml`

- [ ] **Step 1: Write the failing config test**

```python
def test_load_settings_reads_event_research_settings(tmp_path: Path) -> None:
    config_path = tmp_path / "event.yaml"
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

    assert settings.event_research.candidate_market_limit == 200
    assert settings.event_research.default_exit_mode == "repricing_target"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src .venv/bin/pytest tests/unit/test_config.py::test_load_settings_reads_event_research_settings -v`
Expected: FAIL because `Settings` does not yet include `event_research`.

- [ ] **Step 3: Add minimal Phase 2.3 settings and sample config files**

```python
class EventResearchSettings(BaseModel):
    candidate_market_limit: int = Field(gt=0, default=100)
    source_registry_path: str
    response_window_seconds: int = Field(gt=0, default=120)
    max_signal_age_seconds: int = Field(gt=0, default=15)
    min_expected_edge_bps: float = Field(ge=0, default=25)
    default_exit_mode: str = "repricing_target"
```

```yaml
event_research:
  candidate_market_limit: 200
  source_registry_path: configs/source_registry.sample.yaml
  response_window_seconds: 120
  max_signal_age_seconds: 15
  min_expected_edge_bps: 25
  default_exit_mode: repricing_target
```

- [ ] **Step 4: Write the failing event-model test**

```python
from polymarket_arb.domain.models import EnrichedMarketEntry, SourceEventRecord


def test_source_event_record_keeps_source_and_market_links() -> None:
    event = SourceEventRecord(
        source_event_id="source-1",
        source_type="http_json",
        source_key="sec-filing",
        received_timestamp_ms=1_700_000_000_000,
        normalized_payload={"headline": "Form filed"},
        affected_market_ids=["123"],
    )

    assert event.source_key == "sec-filing"
    assert event.affected_market_ids == ["123"]
```

- [ ] **Step 5: Add minimal enriched-market and source-event models**

```python
class EnrichedMarketEntry(MarketCatalogEntry):
    category: str | None = None
    end_date_iso: str | None = None
    resolution_text: str | None = None
    tags: list[str] = Field(default_factory=list)
    source_registry_key: str | None = None


class SourceEventRecord(BaseModel):
    source_event_id: str
    source_type: str
    source_key: str
    received_timestamp_ms: int
    normalized_payload: dict[str, object]
    affected_market_ids: list[str] = Field(default_factory=list)
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `PYTHONPATH=src .venv/bin/pytest tests/unit/test_config.py tests/unit/research/test_event_models.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add src/polymarket_arb/config.py src/polymarket_arb/domain/models.py tests/unit/test_config.py tests/unit/research/test_event_models.py configs/event_research.sample.yaml configs/source_registry.sample.yaml
git commit -m "feat: add phase 2.3 config and models"
```

## Task 2: Expand Gamma Discovery And Build Enriched Candidate Catalogs

**Files:**
- Modify: `src/polymarket_arb/clients/gamma.py`
- Modify: `src/polymarket_arb/catalog/service.py`
- Modify: `src/polymarket_arb/domain/models.py`
- Modify: `tests/unit/clients/test_gamma.py`
- Modify: `tests/unit/catalog/test_service.py`

- [ ] **Step 1: Write the failing Gamma discovery test**

```python
def test_fetch_active_markets_respects_limit() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["limit"] == "2"
        return httpx.Response(
            200,
            json=[
                {"id": "1", "slug": "a", "active": True, "closed": False},
                {"id": "2", "slug": "b", "active": True, "closed": False},
            ],
        )

    client = GammaClient(
        client=httpx.Client(
            base_url="https://gamma-api.polymarket.com",
            transport=httpx.MockTransport(handler),
        )
    )

    markets = client.fetch_active_markets(limit=2)

    assert [market["id"] for market in markets] == ["1", "2"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src .venv/bin/pytest tests/unit/clients/test_gamma.py::test_fetch_active_markets_respects_limit -v`
Expected: FAIL because `fetch_active_markets` does not exist.

- [ ] **Step 3: Add broader active-market discovery to `GammaClient`**

```python
def fetch_active_markets(self, *, limit: int) -> list[dict[str, Any]]:
    response = self._client.get(
        "/markets",
        params={"active": True, "closed": False, "limit": limit},
    )
    response.raise_for_status()
    return list(response.json())
```

- [ ] **Step 4: Write the failing enriched-catalog service test**

```python
def test_build_candidate_catalog_preserves_resolution_text_and_tags() -> None:
    payload = [
        {
            "id": "123",
            "slug": "will-example-happen",
            "question": "Will example happen?",
            "active": True,
            "closed": False,
            "outcomes": ["Yes", "No"],
            "clobTokenIds": ["yes-1", "no-1"],
            "description": "Resolves to YES if Example API says true.",
            "category": "crypto",
            "endDate": "2026-04-01T00:00:00Z",
        }
    ]

    catalog = build_candidate_catalog(payload)

    assert catalog[0].resolution_text == "Resolves to YES if Example API says true."
    assert "objective_source_candidate" in catalog[0].tags
```

- [ ] **Step 5: Add a candidate-catalog builder**

```python
def build_candidate_catalog(markets: list[dict[str, Any]]) -> list[EnrichedMarketEntry]:
    entries: list[EnrichedMarketEntry] = []
    for market in markets:
        token_pair = resolve_binary_token_pair(market)
        if token_pair is None or not market.get("active") or market.get("closed"):
            continue
        entries.append(
            EnrichedMarketEntry(
                market_id=str(market["id"]),
                slug=str(market["slug"]),
                question=str(market.get("question") or market["slug"]),
                yes_token_id=token_pair[0],
                no_token_id=token_pair[1],
                fees_enabled=bool(market.get("feesEnabled", False)),
                max_capital_usd=0.0,
                category=str(market.get("category") or ""),
                end_date_iso=str(market.get("endDate") or ""),
                resolution_text=str(market.get("description") or ""),
                tags=classify_candidate_tags(market),
            )
        )
    return entries
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `PYTHONPATH=src .venv/bin/pytest tests/unit/clients/test_gamma.py tests/unit/catalog/test_service.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add src/polymarket_arb/clients/gamma.py src/polymarket_arb/catalog/service.py src/polymarket_arb/domain/models.py tests/unit/clients/test_gamma.py tests/unit/catalog/test_service.py
git commit -m "feat: add event research catalog discovery"
```

## Task 3: Add Source Registry Loading And Source-Event Normalization

**Files:**
- Create: `src/polymarket_arb/sources/__init__.py`
- Create: `src/polymarket_arb/sources/models.py`
- Create: `src/polymarket_arb/sources/registry.py`
- Create: `src/polymarket_arb/sources/adapters.py`
- Create: `tests/unit/sources/test_registry.py`
- Create: `tests/unit/sources/test_adapters.py`

- [ ] **Step 1: Write the failing source-registry test**

```python
def test_load_source_registry_reads_market_mapping(tmp_path: Path) -> None:
    registry_path = tmp_path / "source_registry.yaml"
    registry_path.write_text(
        dedent(
            """
            sources:
              - key: sec-filing
                source_type: http_json
                url: https://example.com/api
                parser: sec_status
                market_slugs:
                  - will-example-happen
                implied_direction: yes
            """
        ).strip()
    )

    registry = load_source_registry(registry_path)

    assert registry.sources[0].key == "sec-filing"
    assert registry.sources[0].market_slugs == ["will-example-happen"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src .venv/bin/pytest tests/unit/sources/test_registry.py::test_load_source_registry_reads_market_mapping -v`
Expected: FAIL because the `sources` package does not exist.

- [ ] **Step 3: Add registry models and loader**

```python
class SourceDefinition(BaseModel):
    key: str
    source_type: str
    url: str
    parser: str
    market_slugs: list[str]
    implied_direction: str


class SourceRegistry(BaseModel):
    sources: list[SourceDefinition]


def load_source_registry(path: Path) -> SourceRegistry:
    return SourceRegistry.model_validate(yaml.safe_load(path.read_text()))
```

- [ ] **Step 4: Write the failing adapter normalization test**

```python
def test_normalize_http_json_payload_builds_source_event() -> None:
    definition = SourceDefinition(
        key="sec-filing",
        source_type="http_json",
        url="https://example.com/api",
        parser="sec_status",
        market_slugs=["will-example-happen"],
        implied_direction="yes",
    )

    event = normalize_http_json_payload(
        definition=definition,
        payload={"status": "filed", "timestamp": "2026-03-20T10:00:00Z"},
        received_timestamp_ms=1_742_468_400_000,
        affected_market_ids=["123"],
    )

    assert event.source_key == "sec-filing"
    assert event.normalized_payload["status"] == "filed"
```

- [ ] **Step 5: Add minimal source-event normalization**

```python
def normalize_http_json_payload(
    *,
    definition: SourceDefinition,
    payload: dict[str, object],
    received_timestamp_ms: int,
    affected_market_ids: list[str],
) -> SourceEventRecord:
    return SourceEventRecord(
        source_event_id=f"{definition.key}:{received_timestamp_ms}",
        source_type=definition.source_type,
        source_key=definition.key,
        received_timestamp_ms=received_timestamp_ms,
        normalized_payload=dict(payload),
        affected_market_ids=affected_market_ids,
    )
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `PYTHONPATH=src .venv/bin/pytest tests/unit/sources/test_registry.py tests/unit/sources/test_adapters.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add src/polymarket_arb/sources/__init__.py src/polymarket_arb/sources/models.py src/polymarket_arb/sources/registry.py src/polymarket_arb/sources/adapters.py tests/unit/sources/test_registry.py tests/unit/sources/test_adapters.py
git commit -m "feat: add source registry and event normalization"
```

## Task 4: Build Lead-Lag Tracking And Ranking Reports

**Files:**
- Create: `src/polymarket_arb/research/event_lag.py`
- Create: `src/polymarket_arb/research/event_ranking.py`
- Modify: `src/polymarket_arb/reporting/writers.py`
- Create: `tests/unit/research/test_event_lag.py`
- Create: `tests/unit/research/test_event_ranking.py`

- [ ] **Step 1: Write the failing lag-tracker test**

```python
def test_event_lag_tracker_computes_first_move_and_best_entry() -> None:
    tracker = EventLagTracker(response_window_seconds=120, min_expected_edge_bps=25)
    tracker.observe_source_event(
        SourceEventRecord(
            source_event_id="source-1",
            source_type="http_json",
            source_key="sec-filing",
            received_timestamp_ms=1_700_000_000_000,
            normalized_payload={"status": "filed"},
            affected_market_ids=["123"],
        )
    )
    tracker.observe_market_snapshot(
        market_id="123",
        timestamp_ms=1_700_000_005_000,
        best_yes_ask=0.42,
        best_no_ask=0.60,
        yes_size=50,
        no_size=40,
    )

    summary = tracker.finalize_market("123")

    assert summary.time_to_first_move_ms == 5_000
    assert summary.best_entry_edge_bps > 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src .venv/bin/pytest tests/unit/research/test_event_lag.py::test_event_lag_tracker_computes_first_move_and_best_entry -v`
Expected: FAIL because `EventLagTracker` does not exist.

- [ ] **Step 3: Add the lag tracker and response summary model**

```python
class EventLagSummary(BaseModel):
    market_id: str
    source_event_id: str
    time_to_first_move_ms: int = 0
    best_entry_edge_bps: float = 0.0
    max_favorable_move_bps: float = 0.0


class EventLagTracker:
    def __init__(self, *, response_window_seconds: int, min_expected_edge_bps: float) -> None:
        ...
```

- [ ] **Step 4: Write the failing ranking test**

```python
def test_rank_event_markets_prefers_repeatable_edge_over_single_spike() -> None:
    ranked = rank_event_markets(
        [
            {"slug": "steady", "accepted_signal_count": 4, "median_edge_bps": 35, "source_health": 1.0},
            {"slug": "spiky", "accepted_signal_count": 1, "median_edge_bps": 80, "source_health": 0.4},
        ]
    )

    assert ranked[0].slug == "steady"
```

- [ ] **Step 5: Add ranking helper and writers for Phase 2.3 artifacts**

```python
def rank_event_markets(rows: list[dict[str, float]]) -> list[RankedEventMarket]:
    ...


def write_event_lag_summary(output_dir: Path, payload: Any) -> Path:
    ...


def write_event_rankings(output_dir: Path, payload: Any) -> Path:
    ...
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `PYTHONPATH=src .venv/bin/pytest tests/unit/research/test_event_lag.py tests/unit/research/test_event_ranking.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add src/polymarket_arb/research/event_lag.py src/polymarket_arb/research/event_ranking.py src/polymarket_arb/reporting/writers.py tests/unit/research/test_event_lag.py tests/unit/research/test_event_ranking.py
git commit -m "feat: add event lag tracking and rankings"
```

## Task 5: Add Directional Paper Ledger And Event-Paper Runner

**Files:**
- Create: `src/polymarket_arb/portfolio/directional.py`
- Create: `src/polymarket_arb/research/event_paper.py`
- Create: `tests/unit/portfolio/test_directional_ledger.py`
- Create: `tests/unit/research/test_event_paper.py`

- [ ] **Step 1: Write the failing directional-ledger test**

```python
def test_directional_ledger_realizes_pnl_on_exit() -> None:
    ledger = DirectionalLedger(starting_cash_usd=500)
    trade_id = ledger.open_position(
        market_id="123",
        direction="YES",
        size=10,
        entry_price=0.42,
    )

    ledger.close_position(trade_id=trade_id, exit_price=0.58)

    assert ledger.realized_pnl_usd == 1.6
    assert ledger.free_cash_usd == 501.6
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src .venv/bin/pytest tests/unit/portfolio/test_directional_ledger.py::test_directional_ledger_realizes_pnl_on_exit -v`
Expected: FAIL because `DirectionalLedger` does not exist.

- [ ] **Step 3: Add a focused directional ledger**

```python
class DirectionalLedger:
    def __init__(self, *, starting_cash_usd: float) -> None:
        ...

    def open_position(self, *, market_id: str, direction: str, size: float, entry_price: float) -> str:
        ...

    def close_position(self, *, trade_id: str, exit_price: float) -> None:
        ...
```

- [ ] **Step 4: Write the failing event-paper runner test**

```python
def test_event_paper_runner_creates_trade_for_accepted_signal() -> None:
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
        best_ask=0.42,
        available_size=10,
        timestamp_ms=1_700_000_000_000,
    )

    assert result.decision == "trade"
    assert result.trade.direction == "YES"
```

- [ ] **Step 5: Add the event-paper runner**

```python
class EventPaperRunner:
    def __init__(self, *, starting_cash_usd: float, max_total_deployed_usd: float, default_exit_mode: str) -> None:
        ...

    def on_signal(... ) -> EventPaperOutcome:
        ...
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `PYTHONPATH=src .venv/bin/pytest tests/unit/portfolio/test_directional_ledger.py tests/unit/research/test_event_paper.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add src/polymarket_arb/portfolio/directional.py src/polymarket_arb/research/event_paper.py tests/unit/portfolio/test_directional_ledger.py tests/unit/research/test_event_paper.py
git commit -m "feat: add event paper runner"
```

## Task 6: Add CLI Commands, Artifact Writing, And Docs

**Files:**
- Modify: `src/polymarket_arb/cli.py`
- Modify: `src/polymarket_arb/reporting/writers.py`
- Modify: `README.md`
- Create: `tests/integration/test_catalog_expand_cli.py`
- Create: `tests/integration/test_study_source_lag_cli.py`
- Create: `tests/integration/test_run_event_paper_cli.py`
- Create: `tests/fixtures/sources/objective_update.json`

- [ ] **Step 1: Write the failing catalog-expand integration test**

```python
def test_catalog_expand_writes_enriched_catalog(tmp_path: Path, monkeypatch) -> None:
    runner = CliRunner()
    output_path = tmp_path / "catalog.json"
    ...
    result = runner.invoke(
        app,
        [
            "catalog-expand",
            "--config-path",
            str(config_path),
            "--output-path",
            str(output_path),
        ],
    )

    assert result.exit_code == 0
    assert json.loads(output_path.read_text())[0]["resolution_text"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src .venv/bin/pytest tests/integration/test_catalog_expand_cli.py::test_catalog_expand_writes_enriched_catalog -v`
Expected: FAIL because `catalog-expand` does not exist.

- [ ] **Step 3: Add the catalog-expansion command**

```python
@app.command("catalog-expand")
def catalog_expand(
    config_path: Path = typer.Option(..., "--config-path"),
    output_path: Path = typer.Option(..., "--output-path"),
) -> None:
    ...
```

- [ ] **Step 4: Write the failing lag-study integration test**

```python
def test_study_source_lag_writes_summary_and_rankings(tmp_path: Path, monkeypatch) -> None:
    result = runner.invoke(
        app,
        [
            "study-source-lag",
            "--config-path",
            str(config_path),
            "--output-dir",
            str(output_dir),
        ],
    )

    assert result.exit_code == 0
    assert (output_dir / "event_lag_summary.json").exists()
    assert (output_dir / "event_rankings.json").exists()
```

- [ ] **Step 5: Implement `study-source-lag` and artifact writing**

```python
@app.command("study-source-lag")
def study_source_lag(...) -> None:
    ...
```

- [ ] **Step 6: Write the failing event-paper integration test**

```python
def test_run_event_paper_writes_trade_log(tmp_path: Path, monkeypatch) -> None:
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
    assert (output_dir / "summary.json").exists()
    assert (output_dir / "trade_log.json").exists()
```

- [ ] **Step 7: Implement `run-event-paper` and document the workflow**

```python
@app.command("run-event-paper")
def run_event_paper(...) -> None:
    ...
```

- [ ] **Step 8: Run the targeted integration suite**

Run: `PYTHONPATH=src .venv/bin/pytest tests/integration/test_catalog_expand_cli.py tests/integration/test_study_source_lag_cli.py tests/integration/test_run_event_paper_cli.py -v`
Expected: PASS

- [ ] **Step 9: Commit**

```bash
git add src/polymarket_arb/cli.py src/polymarket_arb/reporting/writers.py README.md tests/integration/test_catalog_expand_cli.py tests/integration/test_study_source_lag_cli.py tests/integration/test_run_event_paper_cli.py tests/fixtures/sources/objective_update.json
git commit -m "feat: add phase 2.3 event research cli"
```

## Task 7: Full Verification

**Files:**
- Modify: `README.md`
- Verify: `src/polymarket_arb/...`
- Verify: `tests/...`

- [ ] **Step 1: Run the focused Phase 2.3 unit suite**

Run: `PYTHONPATH=src .venv/bin/pytest tests/unit/test_config.py tests/unit/clients/test_gamma.py tests/unit/catalog/test_service.py tests/unit/research/test_event_models.py tests/unit/sources/test_registry.py tests/unit/sources/test_adapters.py tests/unit/research/test_event_lag.py tests/unit/research/test_event_ranking.py tests/unit/portfolio/test_directional_ledger.py tests/unit/research/test_event_paper.py -v`
Expected: PASS

- [ ] **Step 2: Run the focused Phase 2.3 integration suite**

Run: `PYTHONPATH=src .venv/bin/pytest tests/integration/test_catalog_expand_cli.py tests/integration/test_study_source_lag_cli.py tests/integration/test_run_event_paper_cli.py -v`
Expected: PASS

- [ ] **Step 3: Run the existing smoke suite that Phase 2.3 could affect**

Run: `PYTHONPATH=src .venv/bin/pytest tests/integration/test_study_live_opportunities_cli.py tests/integration/test_run_paper_cli.py tests/unit/test_config.py -v`
Expected: PASS

- [ ] **Step 4: Commit any final doc or fixture adjustments**

```bash
git add README.md tests/fixtures/sources/objective_update.json
git commit -m "docs: finalize phase 2.3 workflow"
```

## Notes For Execution

- Keep the first source universe deliberately tiny. One good source family with clean fixtures is better than three vague ones.
- Do not retrofit the existing pair-arbitrage engine into directional trading. Keep the new event-paper runner isolated so the old path stays stable.
- Prefer replayable JSON artifacts over clever in-memory shortcuts. If a result cannot be replayed, it is not good enough for this phase.
- If candidate-market expansion reveals that most markets are too ambiguous for objective-source mapping, stop and narrow the domain before building more adapters.
