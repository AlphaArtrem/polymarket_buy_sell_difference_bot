from pathlib import Path

from typer.testing import CliRunner

from polymarket_arb.cli import app


def test_run_replay_fails_when_catalog_is_missing(tmp_path: Path) -> None:
    runner = CliRunner()
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    output_dir = tmp_path / "out"
    config_path = tmp_path / "markets.yaml"
    config_path.write_text(Path("configs/markets.sample.yaml").read_text(encoding="utf-8"))

    result = runner.invoke(
        app,
        [
            "run-replay",
            "--config-path",
            str(config_path),
            "--run-dir",
            str(run_dir),
            "--output-dir",
            str(output_dir),
        ],
    )

    assert result.exit_code == 1
    assert "catalog.json" in result.stderr


def test_run_replay_fails_when_events_are_missing(tmp_path: Path) -> None:
    runner = CliRunner()
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    output_dir = tmp_path / "out"
    config_path = tmp_path / "markets.yaml"
    config_path.write_text(Path("configs/markets.sample.yaml").read_text(encoding="utf-8"))
    (run_dir / "catalog.json").write_text(
        """
[
  {
    "market_id": "market-1",
    "slug": "will-btc-be-above-100k",
    "question": "Will BTC be above $100k?",
    "yes_token_id": "yes-token",
    "no_token_id": "no-token",
    "fees_enabled": true,
    "max_capital_usd": 50.0,
    "active": true
  }
]
""".strip()
        + "\n",
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        [
            "run-replay",
            "--config-path",
            str(config_path),
            "--run-dir",
            str(run_dir),
            "--output-dir",
            str(output_dir),
        ],
    )

    assert result.exit_code == 1
    assert "events.jsonl" in result.stderr
