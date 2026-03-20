import json
from pathlib import Path
from textwrap import dedent

from typer.testing import CliRunner

from polymarket_arb.cli import app


def test_run_event_paper_writes_trade_log(tmp_path: Path, monkeypatch) -> None:
    runner = CliRunner()
    output_dir = tmp_path / "out"
    config_path = tmp_path / "event.yaml"
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
        ).strip(),
        encoding="utf-8",
    )
    config_path.write_text(
        dedent(
            f"""
            venue: polymarket
            api:
              gamma_base_url: https://gamma-api.polymarket.com
              clob_base_url: https://clob.polymarket.com
              poll_interval_ms: 500
            event_research:
              candidate_market_limit: 5
              source_registry_path: {registry_path}
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
        ).strip(),
        encoding="utf-8",
    )

    class StubGammaClient:
        def fetch_active_markets(self, *, limit: int) -> list[dict[str, object]]:
            assert limit == 5
            return [
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

    monkeypatch.setattr(
        "polymarket_arb.cli.make_gamma_client",
        lambda settings: StubGammaClient(),
    )

    fixture_path = Path("tests/fixtures/sources/objective_update.json").resolve()
    result = runner.invoke(
        app,
        [
            "run-event-paper",
            "--config-path",
            str(config_path),
            "--output-dir",
            str(output_dir),
            "--source-payload-path",
            str(fixture_path),
        ],
    )

    assert result.exit_code == 0
    assert (output_dir / "summary.json").exists()
    assert (output_dir / "trade_log.json").exists()
    summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
    trade_log = json.loads((output_dir / "trade_log.json").read_text(encoding="utf-8"))
    assert summary["trades"] == 1
    assert trade_log[0]["direction"] == "YES"


def test_run_event_paper_writes_rejections_exits_and_open_positions(
    tmp_path: Path, monkeypatch
) -> None:
    runner = CliRunner()
    output_dir = tmp_path / "out"
    config_path = tmp_path / "event.yaml"
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
        ).strip(),
        encoding="utf-8",
    )
    config_path.write_text(
        dedent(
            f"""
            venue: polymarket
            api:
              gamma_base_url: https://gamma-api.polymarket.com
              clob_base_url: https://clob.polymarket.com
              poll_interval_ms: 500
            event_research:
              candidate_market_limit: 5
              source_registry_path: {registry_path}
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
        ).strip(),
        encoding="utf-8",
    )

    class StubGammaClient:
        def fetch_active_markets(self, *, limit: int) -> list[dict[str, object]]:
            assert limit == 5
            return [
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

    monkeypatch.setattr(
        "polymarket_arb.cli.make_gamma_client",
        lambda settings: StubGammaClient(),
    )

    fixture_path = Path("tests/fixtures/sources/objective_update.json").resolve()
    result = runner.invoke(
        app,
        [
            "run-event-paper",
            "--config-path",
            str(config_path),
            "--output-dir",
            str(output_dir),
            "--source-payload-path",
            str(fixture_path),
        ],
    )

    assert result.exit_code == 0
    assert (output_dir / "rejections.json").exists()
    assert (output_dir / "exit_log.json").exists()
    assert (output_dir / "open_positions.json").exists()
