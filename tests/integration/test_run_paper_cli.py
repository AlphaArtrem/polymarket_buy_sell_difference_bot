import json
from pathlib import Path
from textwrap import dedent

from typer.testing import CliRunner

from polymarket_arb.cli import app
from polymarket_arb.clients.clob import OrderBookSnapshot


def test_run_paper_command_writes_summary_from_real_public_data(
    tmp_path: Path, monkeypatch
) -> None:
    runner = CliRunner()
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

    market = json.loads(
        Path("tests/fixtures/gamma/market_binary.json").read_text(encoding="utf-8")
    )
    market["id"] = "0xabc"
    market["clobTokenIds"] = ["yes-token-abc", "no-token-abc"]
    yes_book = json.loads(
        Path("tests/fixtures/clob/book_yes.json").read_text(encoding="utf-8")
    )
    no_book = json.loads(
        Path("tests/fixtures/clob/book_no.json").read_text(encoding="utf-8")
    )

    class StubGammaClient:
        def fetch_markets_by_slugs(self, slugs: list[str]) -> list[dict[str, object]]:
            assert slugs == ["will-btc-be-above-100k"]
            return [market]

    class StubClobClient:
        def fetch_order_books(self, token_ids: list[str]) -> dict[str, OrderBookSnapshot]:
            assert token_ids == ["yes-token-abc", "no-token-abc"]
            return {
                yes_book["asset_id"]: OrderBookSnapshot.model_validate(yes_book),
                no_book["asset_id"]: OrderBookSnapshot.model_validate(no_book),
            }

    monkeypatch.setattr(
        "polymarket_arb.cli.make_gamma_client",
        lambda settings: StubGammaClient(),
    )
    monkeypatch.setattr(
        "polymarket_arb.cli.make_clob_client",
        lambda settings: StubClobClient(),
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
            "0",
        ],
    )

    assert result.exit_code == 0
    assert json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))[
        "trades"
    ] == 1
