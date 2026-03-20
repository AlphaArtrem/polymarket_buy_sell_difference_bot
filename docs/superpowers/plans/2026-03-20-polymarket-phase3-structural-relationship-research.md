# Polymarket Phase 3 Structural Relationship Research Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a research workflow that scans linked Polymarket markets for structural pricing inconsistencies across mutually exclusive baskets and implication relationships.

**Architecture:** Reuse the current catalog loading, live recording, replay, paired-book state store, and reporting stack. Add a new `structure` package for relationship definitions, registry loading, opportunity scanning, and ranking; expose it through a dedicated CLI command that emits relationship-level artifacts instead of trade execution.

**Tech Stack:** Python 3.9+, `typer`, `pydantic`, `PyYAML`, `pytest`, JSON artifacts

---

## Scope Check

This plan covers one coherent research subsystem: cross-market structural opportunity analysis. It does not include authenticated trading, maker quoting, or multi-venue support.

## File Structure

### Files To Modify

- Modify: `src/polymarket_arb/config.py`
  Add structure-research settings.
- Modify: `src/polymarket_arb/cli.py`
  Add the structural-study command.
- Modify: `src/polymarket_arb/reporting/writers.py`
  Add structure-study writers.
- Modify: `README.md`
  Document the new workflow and artifacts.
- Modify: `tests/unit/test_config.py`
  Cover structure-research settings.

### Files To Create

- Create: `configs/structure_research.sample.yaml`
  Sample config for Phase 3 structure research.
- Create: `configs/structure_registry.sample.yaml`
  Sample relationship definitions.
- Create: `src/polymarket_arb/structure/__init__.py`
  Package marker.
- Create: `src/polymarket_arb/structure/models.py`
  Relationship and opportunity models.
- Create: `src/polymarket_arb/structure/registry.py`
  Registry loader and catalog resolution helpers.
- Create: `src/polymarket_arb/structure/scanner.py`
  Cross-market relationship scanner.
- Create: `src/polymarket_arb/structure/ranking.py`
  Relationship ranking helpers.
- Create: `tests/unit/structure/test_models.py`
  Verify relationship models.
- Create: `tests/unit/structure/test_registry.py`
  Verify registry loading and slug resolution.
- Create: `tests/unit/structure/test_scanner.py`
  Verify mutually exclusive and implication scans.
- Create: `tests/unit/structure/test_ranking.py`
  Verify relationship ranking.
- Create: `tests/integration/test_study_structure_cli.py`
  End-to-end structure-study CLI test.

## Task 1: Add Structure-Research Settings And Models

**Files:**
- Modify: `src/polymarket_arb/config.py`
- Create: `src/polymarket_arb/structure/models.py`
- Modify: `tests/unit/test_config.py`
- Create: `tests/unit/structure/test_models.py`

- [ ] **Step 1: Write the failing config test**

```python
def test_load_settings_reads_structure_research_settings(tmp_path: Path) -> None:
    config_path = tmp_path / "structure.yaml"
    config_path.write_text(
        dedent(
            """
            venue: polymarket
            api:
              gamma_base_url: https://gamma-api.polymarket.com
              clob_base_url: https://clob.polymarket.com
              poll_interval_ms: 500
            structure_research:
              relationship_registry_path: configs/structure_registry.sample.yaml
              min_raw_gap_bps: 25
              min_net_gap_bps: 10
              min_executable_size: 5
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

    assert settings.structure_research.min_raw_gap_bps == 25
    assert settings.structure_research.min_executable_size == 5
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src .venv/bin/pytest tests/unit/test_config.py::test_load_settings_reads_structure_research_settings -v`
Expected: FAIL because `Settings` does not yet include `structure_research`.

- [ ] **Step 3: Add minimal structure-research settings**

```python
class StructureResearchSettings(BaseModel):
    relationship_registry_path: str = "configs/structure_registry.sample.yaml"
    min_raw_gap_bps: float = Field(ge=0, default=25)
    min_net_gap_bps: float = Field(ge=0, default=10)
    min_executable_size: float = Field(gt=0, default=1)
```

- [ ] **Step 4: Write the failing structure-model test**

```python
from polymarket_arb.structure.models import StructureDefinition


def test_structure_definition_accepts_mutually_exclusive_group() -> None:
    definition = StructureDefinition(
        key="election-basket",
        relationship_type="mutually_exclusive_yes",
        market_slugs=["a", "b", "c"],
    )

    assert definition.relationship_type == "mutually_exclusive_yes"
    assert definition.market_slugs == ["a", "b", "c"]
```

- [ ] **Step 5: Add minimal structure models**

```python
class StructureDefinition(BaseModel):
    key: str
    relationship_type: str
    market_slugs: list[str]


class StructureOpportunity(BaseModel):
    key: str
    relationship_type: str
    raw_gap_bps: float
    net_gap_bps: float
    executable_size: float
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `PYTHONPATH=src .venv/bin/pytest tests/unit/test_config.py tests/unit/structure/test_models.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add src/polymarket_arb/config.py src/polymarket_arb/structure/models.py tests/unit/test_config.py tests/unit/structure/test_models.py
git commit -m "feat: add phase 3 structure settings and models"
```

## Task 2: Add Relationship Registry Loading And Catalog Resolution

**Files:**
- Create: `configs/structure_research.sample.yaml`
- Create: `configs/structure_registry.sample.yaml`
- Create: `src/polymarket_arb/structure/registry.py`
- Create: `tests/unit/structure/test_registry.py`

- [ ] **Step 1: Write the failing registry-loading test**

```python
def test_load_structure_registry_reads_relationships(tmp_path: Path) -> None:
    registry_path = tmp_path / "structure_registry.yaml"
    registry_path.write_text(
        dedent(
            """
            relationships:
              - key: election-basket
                relationship_type: mutually_exclusive_yes
                market_slugs:
                  - will-a-win
                  - will-b-win
            """
        ).strip()
    )

    registry = load_structure_registry(registry_path)

    assert registry.relationships[0].key == "election-basket"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src .venv/bin/pytest tests/unit/structure/test_registry.py::test_load_structure_registry_reads_relationships -v`
Expected: FAIL because `structure/registry.py` does not exist.

- [ ] **Step 3: Add registry loading**

```python
class StructureRegistry(BaseModel):
    relationships: list[StructureDefinition]


def load_structure_registry(path: Path) -> StructureRegistry:
    return StructureRegistry.model_validate(yaml.safe_load(path.read_text()))
```

- [ ] **Step 4: Write the failing catalog-resolution test**

```python
def test_resolve_structure_registry_maps_slugs_to_market_ids() -> None:
    registry = StructureRegistry(
        relationships=[
            StructureDefinition(
                key="basket",
                relationship_type="mutually_exclusive_yes",
                market_slugs=["will-a-win", "will-b-win"],
            )
        ]
    )
    catalog = [
        EnrichedMarketEntry(
            market_id="1",
            slug="will-a-win",
            question="Will A win?",
            yes_token_id="yes-a",
            no_token_id="no-a",
            fees_enabled=False,
            max_capital_usd=0.0,
        ),
        EnrichedMarketEntry(
            market_id="2",
            slug="will-b-win",
            question="Will B win?",
            yes_token_id="yes-b",
            no_token_id="no-b",
            fees_enabled=False,
            max_capital_usd=0.0,
        ),
    ]

    resolved = resolve_structure_registry(registry, catalog)

    assert resolved[0].market_ids == ["1", "2"]
```

- [ ] **Step 5: Add slug-to-market resolution**

```python
def resolve_structure_registry(
    registry: StructureRegistry,
    catalog: list[EnrichedMarketEntry],
) -> list[ResolvedStructureDefinition]:
    ...
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `PYTHONPATH=src .venv/bin/pytest tests/unit/structure/test_registry.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add configs/structure_research.sample.yaml configs/structure_registry.sample.yaml src/polymarket_arb/structure/registry.py tests/unit/structure/test_registry.py
git commit -m "feat: add structure registry loading"
```

## Task 3: Build The Structural Opportunity Scanner

**Files:**
- Create: `src/polymarket_arb/structure/scanner.py`
- Create: `tests/unit/structure/test_scanner.py`

- [ ] **Step 1: Write the failing mutually-exclusive basket test**

```python
def test_scan_structure_finds_mutually_exclusive_yes_basket_gap() -> None:
    scanner = StructureScanner(
        min_raw_gap_bps=25,
        min_net_gap_bps=10,
        fee_rate=0.0,
        slippage_buffer=0.0,
        operational_buffer=0.0,
    )

    opportunity = scanner.scan_mutually_exclusive_yes(
        key="election-basket",
        yes_quotes=[
            {"slug": "a", "price": 0.30, "size": 10},
            {"slug": "b", "price": 0.32, "size": 12},
            {"slug": "c", "price": 0.31, "size": 8},
        ],
    )

    assert opportunity is not None
    assert opportunity.raw_gap_bps == 700
    assert opportunity.executable_size == 8
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src .venv/bin/pytest tests/unit/structure/test_scanner.py::test_scan_structure_finds_mutually_exclusive_yes_basket_gap -v`
Expected: FAIL because `StructureScanner` does not exist.

- [ ] **Step 3: Add basket scanning**

```python
def scan_mutually_exclusive_yes(
    self,
    *,
    key: str,
    yes_quotes: list[dict[str, float]],
) -> StructureOpportunity | None:
    ...
```

- [ ] **Step 4: Write the failing implication test**

```python
def test_scan_structure_finds_implication_gap() -> None:
    scanner = StructureScanner(
        min_raw_gap_bps=25,
        min_net_gap_bps=10,
        fee_rate=0.0,
        slippage_buffer=0.0,
        operational_buffer=0.0,
    )

    opportunity = scanner.scan_implication_pair(
        key="a-implies-b",
        yes_child_price=0.62,
        no_parent_price=0.20,
        child_size=9,
        parent_size=7,
    )

    assert opportunity is not None
    assert opportunity.executable_size == 7
```

- [ ] **Step 5: Add implication scanning**

```python
def scan_implication_pair(
    self,
    *,
    key: str,
    yes_child_price: float,
    no_parent_price: float,
    child_size: float,
    parent_size: float,
) -> StructureOpportunity | None:
    ...
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `PYTHONPATH=src .venv/bin/pytest tests/unit/structure/test_scanner.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add src/polymarket_arb/structure/scanner.py tests/unit/structure/test_scanner.py
git commit -m "feat: add structural opportunity scanner"
```

## Task 4: Rank Relationships And Emit Structure Artifacts

**Files:**
- Create: `src/polymarket_arb/structure/ranking.py`
- Modify: `src/polymarket_arb/reporting/writers.py`
- Create: `tests/unit/structure/test_ranking.py`

- [ ] **Step 1: Write the failing ranking test**

```python
from polymarket_arb.structure.ranking import rank_structure_relationships


def test_rank_structure_relationships_prefers_repeatable_large_gaps() -> None:
    ranked = rank_structure_relationships(
        [
            {"key": "steady", "opportunity_count": 5, "best_net_gap_bps": 80, "mean_executable_size": 10},
            {"key": "spike", "opportunity_count": 1, "best_net_gap_bps": 150, "mean_executable_size": 2},
        ]
    )

    assert ranked[0].key == "steady"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src .venv/bin/pytest tests/unit/structure/test_ranking.py::test_rank_structure_relationships_prefers_repeatable_large_gaps -v`
Expected: FAIL because `structure/ranking.py` does not exist.

- [ ] **Step 3: Add structure ranking helper**

```python
def rank_structure_relationships(rows: list[dict[str, object]]) -> list[RankedStructureRelationship]:
    ...
```

- [ ] **Step 4: Write the failing writer test**

```python
def test_write_structure_summary_serializes_pydantic_payload(tmp_path: Path) -> None:
    output_dir = tmp_path / "out"
    path = write_structure_summary(output_dir, {"relationship_count": 2})

    assert path.name == "structure_summary.json"
    assert json.loads(path.read_text())["relationship_count"] == 2
```

- [ ] **Step 5: Add writer helpers for structure summaries and by-relationship reports**

```python
def write_structure_summary(output_dir: Path, payload: Any) -> Path:
    ...


def write_structure_by_relationship(output_dir: Path, payload: Any) -> Path:
    ...
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `PYTHONPATH=src .venv/bin/pytest tests/unit/structure/test_ranking.py tests/unit/test_cli.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add src/polymarket_arb/structure/ranking.py src/polymarket_arb/reporting/writers.py tests/unit/structure/test_ranking.py
git commit -m "feat: add structure ranking and writers"
```

## Task 5: Add The CLI Workflow And Docs

**Files:**
- Modify: `src/polymarket_arb/cli.py`
- Modify: `README.md`
- Create: `tests/integration/test_study_structure_cli.py`

- [ ] **Step 1: Write the failing structure-study CLI test**

```python
def test_study_structure_opportunities_writes_relationship_artifacts(tmp_path: Path, monkeypatch) -> None:
    runner = CliRunner()
    output_dir = tmp_path / "out"
    ...
    result = runner.invoke(
        app,
        [
            "study-structure-opportunities",
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
    assert (output_dir / "structure_summary.json").exists()
    assert (output_dir / "structure_by_relationship.json").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src .venv/bin/pytest tests/integration/test_study_structure_cli.py::test_study_structure_opportunities_writes_relationship_artifacts -v`
Expected: FAIL because the CLI command does not exist.

- [ ] **Step 3: Add the structure-study command**

```python
@app.command("study-structure-opportunities")
def study_structure_opportunities(
    config_path: Path = typer.Option(..., "--config-path"),
    output_dir: Path = typer.Option(..., "--output-dir"),
    duration_seconds: int = typer.Option(300, "--duration-seconds"),
    mode: str | None = typer.Option(None, "--mode"),
) -> None:
    ...
```

- [ ] **Step 4: Wire the scanner into live study flow**

```python
catalog = build_candidate_catalog(...)
registry = load_structure_registry(...)
resolved_relationships = resolve_structure_registry(registry, catalog)
scanner = StructureScanner(...)
```

- [ ] **Step 5: Document the structure-study workflow**

```markdown
- `study-structure-opportunities`: scans linked-market relationships and writes:
  - `structure_summary.json`
  - `structure_by_relationship.json`
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `PYTHONPATH=src .venv/bin/pytest tests/integration/test_study_structure_cli.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add src/polymarket_arb/cli.py README.md tests/integration/test_study_structure_cli.py
git commit -m "feat: add phase 3 structure study cli"
```

## Task 6: Full Verification

**Files:**
- Verify: `src/polymarket_arb/...`
- Verify: `tests/...`
- Verify: `README.md`

- [ ] **Step 1: Run the Phase 3-focused unit suite**

Run: `PYTHONPATH=src .venv/bin/pytest tests/unit/test_config.py tests/unit/structure/test_models.py tests/unit/structure/test_registry.py tests/unit/structure/test_scanner.py tests/unit/structure/test_ranking.py -v`
Expected: PASS

- [ ] **Step 2: Run the structure-study integration suite**

Run: `PYTHONPATH=src .venv/bin/pytest tests/integration/test_study_structure_cli.py -v`
Expected: PASS

- [ ] **Step 3: Run the full repo suite to guard against regressions**

Run: `PYTHONPATH=src .venv/bin/pytest -v`
Expected: PASS

- [ ] **Step 4: Commit any final README or fixture adjustments**

```bash
git add README.md tests/integration/test_study_structure_cli.py
git commit -m "docs: finalize phase 3 structure workflow"
```

## Notes For Execution

- Start with two relationship types only: `mutually_exclusive_yes` and `implies_yes`. Keep the registry extensible, but do not build a giant relationship taxonomy in the first pass.
- Treat negative-risk baskets as a registry/data problem first, not a special engine. If the relationship definitions are clean, the same basket scanner can handle them later.
- Keep the scanner research-only in this phase. Ranking and artifacts are the goal; live execution of structure baskets is a later concern.
- Prefer explicit human-maintained relationship definitions over weak automatic inference. If a relationship is important, encode it clearly in the registry.
