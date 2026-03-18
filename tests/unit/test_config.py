from pathlib import Path
from textwrap import dedent

from polymarket_arb.config import load_settings


def test_load_settings_reads_allowlist_and_risk_caps(tmp_path: Path) -> None:
    config_path = tmp_path / "markets.yaml"
    config_path.write_text(
        dedent(
            """
        venue: polymarket
        api:
          gamma_base_url: https://gamma-api.polymarket.com
          clob_base_url: https://clob.polymarket.com
          poll_interval_ms: 500
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
        ).strip()
    )

    settings = load_settings(config_path)

    assert settings.venue == "polymarket"
    assert settings.api.gamma_base_url == "https://gamma-api.polymarket.com"
    assert settings.api.poll_interval_ms == 500
    assert settings.markets[0].slug == "will-btc-be-above-100k"
    assert settings.portfolio.starting_cash_usd == 500


def test_load_settings_reads_streaming_transport_and_runtime_paths(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "streaming.yaml"
    config_path.write_text(
        dedent(
            """
            venue: polymarket
            api:
              gamma_base_url: https://gamma-api.polymarket.com
              clob_base_url: https://clob.polymarket.com
              market_ws_url: wss://ws-subscriptions-clob.polymarket.com/ws/market
              poll_interval_ms: 500
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
        ).strip()
    )

    settings = load_settings(config_path)

    assert settings.api.market_ws_url.endswith("/ws/market")
    assert settings.runtime.mode == "stream"
    assert settings.runtime.artifact_dir == "artifacts/runtime"
