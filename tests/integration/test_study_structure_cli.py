import json
from pathlib import Path
from textwrap import dedent

from typer.testing import CliRunner

from polymarket_arb.cli import app
from polymarket_arb.clients.clob import OrderBookSnapshot


def test_study_structure_opportunities_writes_relationship_artifacts(
    tmp_path: Path, monkeypatch
) -> None:
    runner = CliRunner()
    output_dir = tmp_path / "out"
    config_path = tmp_path / "structure.yaml"
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
              market_ws_url: wss://ws-subscriptions-clob.polymarket.com/ws/market
              poll_interval_ms: 1
            runtime:
              mode: stream
              artifact_dir: artifacts/runtime
            structure_research:
              relationship_registry_path: {registry_path}
              min_raw_gap_bps: 25
              min_net_gap_bps: 10
              min_executable_size: 5
            markets:
              - slug: will-a-win
                max_capital_usd: 50
              - slug: will-b-win
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

    market_a = json.loads(
        Path("tests/fixtures/gamma/market_binary.json").read_text(encoding="utf-8")
    )
    market_a["id"] = "0xa"
    market_a["slug"] = "will-a-win"
    market_a["question"] = "Will A win?"
    market_a["clobTokenIds"] = ["yes-token-a", "no-token-a"]

    market_b = json.loads(
        Path("tests/fixtures/gamma/market_binary.json").read_text(encoding="utf-8")
    )
    market_b["id"] = "0xb"
    market_b["slug"] = "will-b-win"
    market_b["question"] = "Will B win?"
    market_b["clobTokenIds"] = ["yes-token-b", "no-token-b"]

    yes_book = json.loads(
        Path("tests/fixtures/clob/book_yes.json").read_text(encoding="utf-8")
    )
    no_book = json.loads(
        Path("tests/fixtures/clob/book_no.json").read_text(encoding="utf-8")
    )

    yes_a = dict(yes_book)
    yes_a["asset_id"] = "yes-token-a"
    yes_a["market"] = "0xa"
    yes_a["asks"] = [["0.48", "10"]]

    no_a = dict(no_book)
    no_a["asset_id"] = "no-token-a"
    no_a["market"] = "0xa"
    no_a["asks"] = [["0.60", "10"]]

    yes_b = dict(yes_book)
    yes_b["asset_id"] = "yes-token-b"
    yes_b["market"] = "0xb"
    yes_b["asks"] = [["0.49", "8"]]

    no_b = dict(no_book)
    no_b["asset_id"] = "no-token-b"
    no_b["market"] = "0xb"
    no_b["asks"] = [["0.60", "8"]]

    class StubGammaClient:
        def fetch_markets_by_slugs(self, slugs: list[str]) -> list[dict[str, object]]:
            assert slugs == ["will-a-win", "will-b-win"]
            return [market_a, market_b]

    class StubClobClient:
        def fetch_order_books(self, token_ids: list[str]) -> dict[str, OrderBookSnapshot]:
            assert sorted(token_ids) == sorted(
                ["yes-token-a", "no-token-a", "yes-token-b", "no-token-b"]
            )
            return {
                "yes-token-a": OrderBookSnapshot.model_validate(yes_a),
                "no-token-a": OrderBookSnapshot.model_validate(no_a),
                "yes-token-b": OrderBookSnapshot.model_validate(yes_b),
                "no-token-b": OrderBookSnapshot.model_validate(no_b),
            }

    class StubWsClient:
        async def subscribe_market(self, url: str, asset_ids: list[str]):
            assert sorted(asset_ids) == sorted(
                ["yes-token-a", "no-token-a", "yes-token-b", "no-token-b"]
            )
            if False:
                yield ""

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
    summary = json.loads(
        (output_dir / "structure_summary.json").read_text(encoding="utf-8")
    )
    by_relationship = json.loads(
        (output_dir / "structure_by_relationship.json").read_text(encoding="utf-8")
    )
    assert summary["relationship_count"] == 1
    assert summary["opportunity_count"] == 1
    assert by_relationship[0]["key"] == "election-basket"
