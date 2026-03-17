import json
from pathlib import Path
from textwrap import dedent

from typer.testing import CliRunner

from polymarket_arb.cli import app


def test_analyze_recording_writes_opportunity_summary(tmp_path: Path) -> None:
    runner = CliRunner()
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    output_dir = tmp_path / "out"
    config_path = tmp_path / "markets.yaml"
    config_path.write_text(
        dedent(
            """
            venue: polymarket
            api:
              gamma_base_url: https://gamma-api.polymarket.com
              clob_base_url: https://clob.polymarket.com
              poll_interval_ms: 1
            markets:
              - slug: market-one
                max_capital_usd: 50
            strategy:
              raw_alert_threshold: 0.99
              fee_rate: 0.005
              slippage_buffer: 0.002
              operational_buffer: 0.001
              stale_after_ms: 5000
            portfolio:
              starting_cash_usd: 500
              max_total_deployed_usd: 200
            """
        ).strip(),
        encoding="utf-8",
    )
    (run_dir / "catalog.json").write_text(
        """
[
  {
    "market_id": "m1",
    "slug": "market-one",
    "question": "Market one?",
    "yes_token_id": "yes-1",
    "no_token_id": "no-1",
    "fees_enabled": false,
    "max_capital_usd": 50.0,
    "active": true
  }
]
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (run_dir / "events.jsonl").write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "market_id": "m1",
                        "side": "YES",
                        "asks": [{"price": 0.48, "size": 100.0}],
                        "timestamp_ms": 1000,
                    }
                ),
                json.dumps(
                    {
                        "market_id": "m1",
                        "side": "NO",
                        "asks": [{"price": 0.49, "size": 100.0}],
                        "timestamp_ms": 1000,
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        [
            "analyze-recording",
            "--config-path",
            str(config_path),
            "--run-dir",
            str(run_dir),
            "--output-dir",
            str(output_dir),
        ],
    )

    assert result.exit_code == 0
    summary = json.loads(
        (output_dir / "opportunity_summary.json").read_text(encoding="utf-8")
    )
    assert summary["event_count"] == 2
    assert summary["paired_snapshot_count"] == 1
    assert summary["raw_opportunity_count"] == 1
    assert summary["post_cost_opportunity_count"] == 1
