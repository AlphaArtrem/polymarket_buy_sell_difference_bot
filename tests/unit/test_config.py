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


def test_load_settings_reads_research_thresholds(tmp_path: Path) -> None:
    config_path = tmp_path / "research.yaml"
    config_path.write_text(
        dedent(
            """
            venue: polymarket
            api:
              gamma_base_url: https://gamma-api.polymarket.com
              clob_base_url: https://clob.polymarket.com
              poll_interval_ms: 500
            research:
              keep_min_paired_snapshots_per_minute: 8
              keep_min_post_cost_opportunities_per_minute: 1
              keep_min_total_time_in_edge_ms: 3000
              keep_min_best_net_edge_bps: 15
              keep_min_max_window_ms: 1500
              watch_min_paired_snapshots_per_minute: 3
              watch_min_post_cost_opportunities_per_minute: 0.2
              watch_min_best_net_edge_bps: 5
              low_sample_paired_snapshot_floor: 5
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
        ).strip()
    )

    settings = load_settings(config_path)

    assert settings.research.keep_min_best_net_edge_bps == 15
    assert settings.research.watch_min_post_cost_opportunities_per_minute == 0.2
    assert settings.research.low_sample_paired_snapshot_floor == 5
