import json
from pathlib import Path
from textwrap import dedent

from typer.testing import CliRunner

from polymarket_arb.cli import app
from polymarket_arb.domain.models import MarketCatalogEntry


def test_bench_latency_command_writes_summary_artifact(
    tmp_path: Path, monkeypatch
) -> None:
    runner = CliRunner()
    output_path = tmp_path / "latency.json"
    config_path = tmp_path / "markets.yaml"
    config_path.write_text(
        dedent(
            """
            venue: polymarket
            api:
              gamma_base_url: https://gamma-api.polymarket.com
              clob_base_url: https://clob.polymarket.com
              market_ws_url: wss://ws-subscriptions-clob.polymarket.com/ws/market
              poll_interval_ms: 1
            runtime:
              mode: stream
              artifact_dir: artifacts/runtime
              polygon_rpc_url: https://polygon-rpc.example
            markets:
              - slug: will-btc-be-above-100k
                max_capital_usd: 50
            strategy:
              raw_alert_threshold: 0.99
              fee_rate: 0.01
              slippage_buffer: 0.005
              operational_buffer: 0.005
              stale_after_ms: 5000
            portfolio:
              starting_cash_usd: 500
              max_total_deployed_usd: 200
            """
        ).strip(),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "polymarket_arb.cli.measure_http_endpoint",
        lambda *args, **kwargs: [12.0, 14.0, 18.0],
    )
    monkeypatch.setattr(
        "polymarket_arb.cli.measure_websocket_connect",
        lambda *args, **kwargs: [20.0, 22.0, 24.0],
    )
    monkeypatch.setattr(
        "polymarket_arb.cli.refresh_catalog",
        lambda settings: [
            MarketCatalogEntry(
                market_id="0xabc",
                slug="will-btc-be-above-100k",
                question="Will BTC be above $100k?",
                yes_token_id="yes-token-abc",
                no_token_id="no-token-abc",
                fees_enabled=True,
                max_capital_usd=50,
            )
        ],
    )

    result = runner.invoke(
        app,
        [
            "bench-latency",
            "--config-path",
            str(config_path),
            "--output-path",
            str(output_path),
            "--samples",
            "3",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["gamma"]["p50_ms"] == 14.0
    assert payload["market_ws_connect"]["p50_ms"] == 22.0
    assert payload["polygon_rpc"]["count"] == 3
