import json
from pathlib import Path
from textwrap import dedent

from typer.testing import CliRunner

from polymarket_arb.cli import app
from polymarket_arb.clients.clob import OrderBookSnapshot


def test_run_paper_streaming_mode_writes_summary_and_feed_health(
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
              market_ws_url: wss://ws-subscriptions-clob.polymarket.com/ws/market
              poll_interval_ms: 1
            runtime:
              mode: stream
              artifact_dir: artifacts/runtime
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
    initial_yes_book = dict(yes_book)
    initial_yes_book["asks"] = [["0.60", "10"]]
    initial_no_book = dict(no_book)
    initial_no_book["asks"] = [["0.60", "10"]]

    class StubGammaClient:
        def fetch_markets_by_slugs(self, slugs: list[str]) -> list[dict[str, object]]:
            assert slugs == ["will-btc-be-above-100k"]
            return [market]

    class StubClobClient:
        def fetch_order_books(self, token_ids: list[str]) -> dict[str, OrderBookSnapshot]:
            assert token_ids == ["yes-token-abc", "no-token-abc"]
            return {
                initial_yes_book["asset_id"]: OrderBookSnapshot.model_validate(
                    initial_yes_book
                ),
                initial_no_book["asset_id"]: OrderBookSnapshot.model_validate(
                    initial_no_book
                ),
            }

    class StubWsClient:
        async def subscribe_market(self, url: str, asset_ids: list[str]):
            assert asset_ids == ["yes-token-abc", "no-token-abc"]
            yield json.dumps(
                {
                    "event_type": "book",
                    "asset_id": "yes-token-abc",
                    "asks": [["0.43", "10"]],
                    "timestamp": 1_700_000_000_010,
                }
            )
            yield json.dumps(
                {
                    "event_type": "book",
                    "asset_id": "no-token-abc",
                    "asks": [["0.54", "10"]],
                    "timestamp": 1_700_000_000_011,
                }
            )

    monkeypatch.setattr(
        "polymarket_arb.cli.make_gamma_client",
        lambda settings: StubGammaClient(),
    )
    monkeypatch.setattr(
        "polymarket_arb.cli.make_clob_client",
        lambda settings: StubClobClient(),
    )
    monkeypatch.setattr(
        "polymarket_arb.cli.make_clob_ws_client",
        lambda settings: StubWsClient(),
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
            "--mode",
            "stream",
        ],
    )

    assert result.exit_code == 0
    assert json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))[
        "trades"
    ] == 1
    feed_health = json.loads(
        (output_dir / "feed_health.json").read_text(encoding="utf-8")
    )
    assert feed_health["mode"] == "stream"
    assert feed_health["events_seen"] >= 4
