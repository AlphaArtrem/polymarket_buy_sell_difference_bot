from pathlib import Path

from typer.testing import CliRunner

from polymarket_arb.cli import app
from polymarket_arb.domain.events import OrderBookEvent
from polymarket_arb.domain.models import BookLevel, MarketCatalogEntry
from polymarket_arb.recording.storage import JsonlEventStore


def test_run_replay_command_writes_summary(tmp_path: Path) -> None:
    runner = CliRunner()
    run_dir = tmp_path / "run"
    output_dir = tmp_path / "out"
    config_path = tmp_path / "markets.yaml"
    config_path.write_text(Path("configs/markets.sample.yaml").read_text())

    store = JsonlEventStore(run_dir)
    store.write_catalog(
        [
            MarketCatalogEntry(
                market_id="market-1",
                slug="will-btc-be-above-100k",
                question="Will BTC be above $100k?",
                yes_token_id="yes-token",
                no_token_id="no-token",
                fees_enabled=True,
                max_capital_usd=50,
            )
        ]
    )
    store.append(
        OrderBookEvent(
            market_id="market-1",
            side="YES",
            asks=[BookLevel(price=0.43, size=10)],
            timestamp_ms=1000,
        )
    )
    store.append(
        OrderBookEvent(
            market_id="market-1",
            side="NO",
            asks=[BookLevel(price=0.54, size=10)],
            timestamp_ms=1001,
        )
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

    assert result.exit_code == 0
    assert (output_dir / "summary.json").exists()


def test_run_paper_command_writes_summary_with_stub_adapter(
    tmp_path: Path, monkeypatch
) -> None:
    runner = CliRunner()
    output_dir = tmp_path / "out"
    config_path = tmp_path / "markets.yaml"
    config_path.write_text(Path("configs/markets.sample.yaml").read_text())

    class StubAdapter:
        def iter_events(self, limit_seconds: int = 60):
            yield OrderBookEvent(
                market_id="market-1",
                side="YES",
                asks=[BookLevel(price=0.43, size=10)],
                timestamp_ms=1000,
            )
            yield OrderBookEvent(
                market_id="market-1",
                side="NO",
                asks=[BookLevel(price=0.54, size=10)],
                timestamp_ms=1001,
            )

    monkeypatch.setattr(
        "polymarket_arb.cli.refresh_catalog",
        lambda settings: [
            MarketCatalogEntry(
                market_id="market-1",
                slug="will-btc-be-above-100k",
                question="Will BTC be above $100k?",
                yes_token_id="yes-token",
                no_token_id="no-token",
                fees_enabled=True,
                max_capital_usd=50,
            )
        ],
    )
    monkeypatch.setattr(
        "polymarket_arb.cli.build_live_adapter",
        lambda settings, catalog: StubAdapter(),
    )

    result = runner.invoke(
        app,
        [
            "run-paper",
            "--config-path",
            str(config_path),
            "--output-dir",
            str(output_dir),
            "--duration-seconds",
            "1",
        ],
    )

    assert result.exit_code == 0
    assert (output_dir / "summary.json").exists()


def test_record_live_command_writes_events_with_stub_adapter(
    tmp_path: Path, monkeypatch
) -> None:
    runner = CliRunner()
    run_dir = tmp_path / "run"
    config_path = tmp_path / "markets.yaml"
    config_path.write_text(Path("configs/markets.sample.yaml").read_text())

    class StubAdapter:
        def iter_events(self, limit_seconds: int = 60):
            yield OrderBookEvent(
                market_id="market-1",
                side="YES",
                asks=[BookLevel(price=0.43, size=10)],
                timestamp_ms=1000,
            )

    monkeypatch.setattr(
        "polymarket_arb.cli.refresh_catalog",
        lambda settings: [
            MarketCatalogEntry(
                market_id="market-1",
                slug="will-btc-be-above-100k",
                question="Will BTC be above $100k?",
                yes_token_id="yes-token",
                no_token_id="no-token",
                fees_enabled=True,
                max_capital_usd=50,
            )
        ],
    )
    monkeypatch.setattr(
        "polymarket_arb.cli.build_live_adapter",
        lambda settings, catalog: StubAdapter(),
    )

    result = runner.invoke(
        app,
        [
            "record-live",
            "--config-path",
            str(config_path),
            "--run-dir",
            str(run_dir),
            "--duration-seconds",
            "1",
        ],
    )

    assert result.exit_code == 0
    assert (run_dir / "events.jsonl").exists()
