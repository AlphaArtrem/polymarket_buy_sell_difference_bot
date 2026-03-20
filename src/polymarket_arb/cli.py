import json
from datetime import datetime
from pathlib import Path
from typing import List

import typer

from polymarket_arb.adapters.live import LiveAdapter
from polymarket_arb.catalog.service import (
    build_candidate_catalog,
    refresh_catalog as refresh_catalog_service,
)
from polymarket_arb.clients.clob import ClobClient
from polymarket_arb.clients.clob import ClobWebSocketClient
from polymarket_arb.clients.gamma import GammaClient
from polymarket_arb.recording.recorder import Recorder
from polymarket_arb.config import Settings, load_settings
from polymarket_arb.domain.models import MarketCatalogEntry
from polymarket_arb.engine import TradingEngine
from polymarket_arb.ops.latency import (
    measure_http_endpoint,
    measure_websocket_connect,
    measure_websocket_subscription,
)
from polymarket_arb.recording.storage import JsonlEventStore, ReplayInputError
from polymarket_arb.adapters.replay import ReplayAdapter
from polymarket_arb.research.opportunities import analyze_recorded_opportunities
from polymarket_arb.research.event_lag import EventLagSummary, EventLagTracker
from polymarket_arb.research.event_paper import EventPaperRunner
from polymarket_arb.research.event_ranking import RankedEventMarket, rank_event_markets
from polymarket_arb.research.market_quality import MarketQualityReport, MarketQualityTracker
from polymarket_arb.reporting.writers import (
    write_catalog_snapshot,
    write_event_lag_summary,
    write_event_rankings,
    write_feed_health,
    write_latency_summary,
    write_market_quality_by_market,
    write_market_quality_summary,
    write_run_summary,
    write_trade_log,
)
from polymarket_arb.sources.adapters import normalize_http_json_payload
from polymarket_arb.sources.registry import load_source_registry

app = typer.Typer(no_args_is_help=True)


def make_gamma_client(settings: Settings) -> GammaClient:
    return GammaClient(base_url=settings.api.gamma_base_url)


def make_clob_client(settings: Settings) -> ClobClient:
    return ClobClient(base_url=settings.api.clob_base_url)


def make_clob_ws_client(settings: Settings) -> ClobWebSocketClient:
    return ClobWebSocketClient()


def refresh_catalog(settings: Settings) -> List[MarketCatalogEntry]:
    return refresh_catalog_service(
        gamma_client=make_gamma_client(settings),
        selections=settings.markets,
    )


def expand_candidate_catalog(settings: Settings) -> list[MarketCatalogEntry]:
    markets = make_gamma_client(settings).fetch_active_markets(
        limit=settings.event_research.candidate_market_limit
    )
    return build_candidate_catalog(markets)


def resolve_config_relative_path(config_path: Path, raw_path: str) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        return path
    return config_path.parent / path


def load_source_payload(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def coerce_timestamp_ms(value: object) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        if value.isdigit():
            return int(value)
        return int(datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp() * 1000)
    raise ValueError(f"Unsupported timestamp value: {value!r}")


def build_source_lag_outputs(
    settings: Settings,
    *,
    config_path: Path,
    source_payload_path: Path,
) -> tuple[list[EventLagSummary], list[RankedEventMarket]]:
    catalog = expand_candidate_catalog(settings)
    registry = load_source_registry(
        resolve_config_relative_path(
            config_path,
            settings.event_research.source_registry_path,
        )
    )
    payload = load_source_payload(source_payload_path)
    tracker = EventLagTracker(
        response_window_seconds=settings.event_research.response_window_seconds,
        min_expected_edge_bps=settings.event_research.min_expected_edge_bps,
    )
    market_by_slug = {entry.slug: entry for entry in catalog}
    summaries: list[EventLagSummary] = []
    ranking_rows: list[dict[str, object]] = []

    received_timestamp_ms = coerce_timestamp_ms(
        payload.get("received_timestamp_ms", payload.get("timestamp"))
    )
    market_timestamp_ms = coerce_timestamp_ms(
        payload.get("market_timestamp_ms", received_timestamp_ms)
    )
    best_yes_ask = float(payload.get("best_yes_ask", 0.0))
    best_no_ask = float(payload.get("best_no_ask", 0.0))
    yes_size = float(payload.get("yes_size", 0.0))
    no_size = float(payload.get("no_size", 0.0))

    for definition in registry.sources:
        affected_markets = [
            market_by_slug[slug]
            for slug in definition.market_slugs
            if slug in market_by_slug
        ]
        if not affected_markets:
            continue
        event = normalize_http_json_payload(
            definition=definition,
            payload=payload,
            received_timestamp_ms=received_timestamp_ms,
            affected_market_ids=[entry.market_id for entry in affected_markets],
        )
        tracker.observe_source_event(event)
        for entry in affected_markets:
            tracker.observe_market_snapshot(
                market_id=entry.market_id,
                timestamp_ms=market_timestamp_ms,
                best_yes_ask=best_yes_ask,
                best_no_ask=best_no_ask,
                yes_size=yes_size,
                no_size=no_size,
            )
            summary = tracker.finalize_market(entry.market_id)
            summaries.append(summary)
            ranking_rows.append(
                {
                    "slug": entry.slug,
                    "accepted_signal_count": int(
                        summary.best_entry_edge_bps
                        >= settings.event_research.min_expected_edge_bps
                    ),
                    "median_edge_bps": summary.best_entry_edge_bps,
                    "source_health": 1.0,
                }
            )

    return summaries, rank_event_markets(ranking_rows)


def build_event_paper_outputs(
    settings: Settings,
    *,
    config_path: Path,
    source_payload_path: Path,
) -> tuple[dict[str, object], list[object]]:
    summaries, _ = build_source_lag_outputs(
        settings,
        config_path=config_path,
        source_payload_path=source_payload_path,
    )
    summary_by_market_id = {summary.market_id: summary for summary in summaries}
    catalog = expand_candidate_catalog(settings)
    registry = load_source_registry(
        resolve_config_relative_path(
            config_path,
            settings.event_research.source_registry_path,
        )
    )
    payload = load_source_payload(source_payload_path)
    market_by_slug = {entry.slug: entry for entry in catalog}
    runner = EventPaperRunner(
        starting_cash_usd=settings.portfolio.starting_cash_usd,
        max_total_deployed_usd=settings.portfolio.max_total_deployed_usd,
        default_exit_mode=settings.event_research.default_exit_mode,
    )
    outcomes = []
    for definition in registry.sources:
        direction = definition.implied_direction.upper()
        best_ask_key = "best_yes_ask" if direction == "YES" else "best_no_ask"
        available_size_key = "yes_size" if direction == "YES" else "no_size"
        for slug in definition.market_slugs:
            entry = market_by_slug.get(slug)
            if entry is None:
                continue
            expected_edge_bps = summary_by_market_id.get(
                entry.market_id,
                EventLagSummary(market_id=entry.market_id, source_event_id=""),
            ).best_entry_edge_bps
            outcomes.append(
                runner.on_signal(
                    market_id=entry.market_id,
                    slug=entry.slug,
                    direction=direction,
                    expected_edge_bps=expected_edge_bps,
                    best_ask=float(payload.get(best_ask_key, 0.0)),
                    available_size=float(payload.get(available_size_key, 0.0)),
                    timestamp_ms=coerce_timestamp_ms(
                        payload.get("market_timestamp_ms", payload.get("timestamp"))
                    ),
                )
            )

    trade_log = [outcome.trade for outcome in outcomes if outcome.trade is not None]
    summary = {
        "trades": len(trade_log),
        "rejections": sum(1 for outcome in outcomes if outcome.decision != "trade"),
        "starting_cash_usd": settings.portfolio.starting_cash_usd,
        "free_cash_usd": runner.ledger.free_cash_usd,
        "deployed_cost_basis_usd": runner.ledger.deployed_cost_basis_usd,
        "realized_pnl_usd": runner.ledger.realized_pnl_usd,
        "default_exit_mode": settings.event_research.default_exit_mode,
    }
    return summary, trade_log


def build_live_adapter(
    settings: Settings,
    catalog: list[MarketCatalogEntry],
    *,
    runtime_mode: str | None = None,
) -> LiveAdapter:
    return LiveAdapter.from_settings(
        settings,
        catalog=catalog,
        clob_client=make_clob_client(settings),
        clob_ws_client=make_clob_ws_client(settings),
        runtime_mode=runtime_mode,
    )


def resolve_catalog_output_path(
    settings: Settings, output_path: Path | None
) -> Path:
    if output_path is not None:
        return output_path
    if settings.api.catalog_output_path:
        return Path(settings.api.catalog_output_path)
    return Path("artifacts/catalog.json")


def resolve_live_adapter(
    settings: Settings,
    catalog: list[MarketCatalogEntry],
    *,
    runtime_mode: str | None = None,
) -> LiveAdapter:
    if runtime_mode is None:
        return build_live_adapter(settings, catalog)
    return build_live_adapter(settings, catalog, runtime_mode=runtime_mode)


def resolve_feed_health(adapter: object, *, mode: str | None = None) -> dict[str, int | str]:
    if hasattr(adapter, "feed_health"):
        feed_health = getattr(adapter, "feed_health")
        if callable(feed_health):
            return feed_health()
    return {
        "mode": mode or "unknown",
        "events_seen": 0,
        "stream_messages_seen": 0,
        "stale_feed_events": 0,
        "reconnects": 0,
    }


def build_market_quality_summary_payload(
    report: MarketQualityReport,
    *,
    config_path: Path,
    thresholds: dict[str, object],
    feed_health: dict[str, int | str] | None = None,
) -> dict[str, object]:
    stream_message_count = report.stream_message_count
    if feed_health is not None:
        stream_message_count = int(feed_health.get("stream_messages_seen", 0))

    return {
        "config_path": str(config_path),
        "run_duration_seconds": report.run_duration_seconds,
        "event_count": report.event_count,
        "stream_message_count": stream_message_count,
        "paired_snapshot_count": report.paired_snapshot_count,
        "raw_opportunity_count": report.raw_opportunity_count,
        "post_cost_opportunity_count": report.post_cost_opportunity_count,
        "opportunity_window_count": report.opportunity_window_count,
        "classification_counts": report.classification_counts,
        "top_markets": {
            status: [
                {
                    "market_id": market.market_id,
                    "slug": market.slug,
                    "best_net_edge_bps": market.best_net_edge_bps,
                }
                for market in sorted(
                    (item for item in report.markets if item.status == status),
                    key=lambda item: (-item.best_net_edge_bps, item.slug),
                )[:5]
            ]
            for status in ("keep", "watch", "drop")
        },
        "thresholds": thresholds,
    }


def build_market_quality_by_market_payload(
    report: MarketQualityReport,
) -> list[dict[str, object]]:
    status_rank = {"keep": 0, "watch": 1, "drop": 2}
    return [
        market.model_dump()
        for market in sorted(
            report.markets,
            key=lambda item: (status_rank.get(item.status, 99), -item.best_net_edge_bps, item.slug),
        )
    ]


@app.command("bench-latency")
def bench_latency(
    config_path: Path = typer.Option(..., "--config-path"),
    output_path: Path = typer.Option(..., "--output-path"),
    samples: int = typer.Option(10, "--samples"),
) -> None:
    """Benchmark public endpoints for VPS placement and streaming setup."""
    settings = load_settings(config_path)
    catalog = refresh_catalog(settings)
    if not catalog:
        typer.echo("No active curated binary markets were resolved from Gamma.", err=True)
        raise typer.Exit(code=1)
    first_market = catalog[0]
    summaries = {
        "gamma": measure_http_endpoint(
            settings.api.gamma_base_url,
            path="/markets",
            params={"slug": first_market.slug},
            samples=samples,
        ),
        "clob_rest": measure_http_endpoint(
            settings.api.clob_base_url,
            method="POST",
            path="/books",
            json_body=[
                {"token_id": first_market.yes_token_id},
                {"token_id": first_market.no_token_id},
            ],
            samples=samples,
        ),
        "market_ws_connect": measure_websocket_connect(
            settings.api.market_ws_url,
            subscription_payload={
                "assets_ids": [first_market.yes_token_id, first_market.no_token_id],
                "type": "market",
            },
            samples=samples,
        ),
    }
    summaries.update(
        measure_websocket_subscription(
            settings.api.market_ws_url,
            subscription_payload={
                "assets_ids": [first_market.yes_token_id, first_market.no_token_id],
                "type": "market",
            },
            samples=samples,
        )
    )
    if settings.runtime.polygon_rpc_url:
        summaries["polygon_rpc"] = measure_http_endpoint(
            settings.runtime.polygon_rpc_url,
            method="POST",
            json_body={"jsonrpc": "2.0", "id": 1, "method": "eth_blockNumber", "params": []},
            samples=samples,
        )
    payload = {
        name: measure_http_summary
        for name, measure_http_summary in (
            (name, summarize_endpoint_samples(values))
            for name, values in summaries.items()
        )
    }
    write_latency_summary(output_path, payload)
    typer.echo(f"Wrote latency summary to {output_path}")


def summarize_endpoint_samples(samples_ms: list[float]) -> dict[str, float]:
    from polymarket_arb.ops.latency import summarize_samples

    return summarize_samples(samples_ms)


@app.command("catalog-refresh")
def catalog_refresh(
    config_path: Path = typer.Option(..., "--config-path"),
    output_path: Path | None = typer.Option(None, "--output-path"),
) -> None:
    """Refresh the curated market catalog."""
    settings = load_settings(config_path)
    catalog = refresh_catalog(settings)
    if not catalog:
        typer.echo("No active curated binary markets were resolved from Gamma.", err=True)
        raise typer.Exit(code=1)
    target_path = resolve_catalog_output_path(settings, output_path)
    write_catalog_snapshot(target_path, catalog)
    typer.echo(f"Wrote {len(catalog)} catalog entries to {target_path}")


@app.command("catalog-expand")
def catalog_expand(
    config_path: Path = typer.Option(..., "--config-path"),
    output_path: Path = typer.Option(..., "--output-path"),
) -> None:
    """Expand the candidate market catalog for objective-source research."""
    settings = load_settings(config_path)
    catalog = expand_candidate_catalog(settings)
    if not catalog:
        typer.echo("No active candidate binary markets were resolved from Gamma.", err=True)
        raise typer.Exit(code=1)
    write_catalog_snapshot(output_path, catalog)
    typer.echo(f"Wrote {len(catalog)} enriched catalog entries to {output_path}")


@app.command("record-live")
def record_live(
    config_path: Path = typer.Option(..., "--config-path"),
    run_dir: Path = typer.Option(..., "--run-dir"),
    duration_seconds: int = typer.Option(60, "--duration-seconds"),
    mode: str | None = typer.Option(None, "--mode"),
) -> None:
    """Record normalized live market events."""
    settings = load_settings(config_path)
    catalog = refresh_catalog(settings)
    if not catalog:
        typer.echo("No active curated binary markets were resolved from Gamma.", err=True)
        raise typer.Exit(code=1)
    adapter = resolve_live_adapter(settings, catalog, runtime_mode=mode)
    store = JsonlEventStore(run_dir)
    recorder = Recorder(store)
    recorder.start_run(catalog)
    for event in adapter.iter_events(limit_seconds=duration_seconds):
        recorder.record(event)
    write_feed_health(
        run_dir / "feed_health.json",
        resolve_feed_health(adapter, mode=mode or settings.runtime.mode),
    )


@app.command("run-replay")
def run_replay(
    config_path: Path = typer.Option(..., "--config-path"),
    run_dir: Path = typer.Option(..., "--run-dir"),
    output_dir: Path = typer.Option(..., "--output-dir"),
) -> None:
    """Run replay mode on recorded data."""
    settings = load_settings(config_path)
    store = JsonlEventStore(run_dir)
    try:
        store.validate_replay_inputs()
    except ReplayInputError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
    adapter = ReplayAdapter(store)
    catalog = store.read_catalog(required=True)
    engine = TradingEngine.from_settings(settings, catalog)
    summary = engine.run(adapter.iter_events())
    write_run_summary(output_dir, summary)


@app.command("run-paper")
def run_paper(
    config_path: Path = typer.Option(..., "--config-path"),
    output_dir: Path = typer.Option(..., "--output-dir"),
    duration_seconds: int = typer.Option(60, "--duration-seconds"),
    mode: str | None = typer.Option(None, "--mode"),
) -> None:
    """Run live paper-trading mode."""
    settings = load_settings(config_path)
    catalog = refresh_catalog(settings)
    if not catalog:
        typer.echo("No active curated binary markets were resolved from Gamma.", err=True)
        raise typer.Exit(code=1)
    adapter = resolve_live_adapter(settings, catalog, runtime_mode=mode)
    engine = TradingEngine.from_settings(settings, catalog)
    summary = engine.run(adapter.iter_events(limit_seconds=duration_seconds))
    write_run_summary(output_dir, summary)
    write_feed_health(
        output_dir / "feed_health.json",
        resolve_feed_health(adapter, mode=mode or settings.runtime.mode),
    )


@app.command("study-live-opportunities")
def study_live_opportunities(
    config_path: Path = typer.Option(..., "--config-path"),
    output_dir: Path = typer.Option(..., "--output-dir"),
    duration_seconds: int = typer.Option(300, "--duration-seconds"),
    mode: str | None = typer.Option("stream", "--mode"),
) -> None:
    """Study live stream market quality without invoking the trading engine."""
    settings = load_settings(config_path)
    catalog = refresh_catalog(settings)
    if not catalog:
        typer.echo("No active curated binary markets were resolved from Gamma.", err=True)
        raise typer.Exit(code=1)

    adapter = resolve_live_adapter(settings, catalog, runtime_mode=mode)
    tracker = MarketQualityTracker(
        catalog=catalog,
        stale_after_ms=settings.strategy.stale_after_ms,
        fee_rate=settings.strategy.fee_rate,
        slippage_buffer=settings.strategy.slippage_buffer,
        operational_buffer=settings.strategy.operational_buffer,
        research=settings.research,
    )
    for event in adapter.iter_events(limit_seconds=duration_seconds):
        tracker.observe(event)

    feed_health = resolve_feed_health(adapter, mode=mode or settings.runtime.mode)
    tracker.note_stream_message(int(feed_health.get("stream_messages_seen", 0)))
    report = tracker.finalize(run_duration_seconds=max(duration_seconds, 0))
    write_market_quality_summary(
        output_dir,
        build_market_quality_summary_payload(
            report,
            config_path=config_path,
            thresholds=settings.research.model_dump(),
            feed_health=feed_health,
        ),
    )
    write_market_quality_by_market(
        output_dir,
        build_market_quality_by_market_payload(report),
    )
    write_feed_health(output_dir / "feed_health.json", feed_health)


@app.command("study-source-lag")
def study_source_lag(
    config_path: Path = typer.Option(..., "--config-path"),
    output_dir: Path = typer.Option(..., "--output-dir"),
    source_payload_path: Path = typer.Option(
        Path("tests/fixtures/sources/objective_update.json"),
        "--source-payload-path",
    ),
) -> None:
    """Study source-to-market lag using replayable source payloads."""
    settings = load_settings(config_path)
    summaries, rankings = build_source_lag_outputs(
        settings,
        config_path=config_path,
        source_payload_path=source_payload_path,
    )
    if not summaries:
        typer.echo("No source-linked candidate markets were resolved.", err=True)
        raise typer.Exit(code=1)
    write_event_lag_summary(output_dir, summaries)
    write_event_rankings(output_dir, rankings)


@app.command("run-event-paper")
def run_event_paper(
    config_path: Path = typer.Option(..., "--config-path"),
    output_dir: Path = typer.Option(..., "--output-dir"),
    source_payload_path: Path = typer.Option(
        Path("tests/fixtures/sources/objective_update.json"),
        "--source-payload-path",
    ),
) -> None:
    """Run one-sided event paper trading from replayable source payloads."""
    settings = load_settings(config_path)
    summary, trade_log = build_event_paper_outputs(
        settings,
        config_path=config_path,
        source_payload_path=source_payload_path,
    )
    write_run_summary(output_dir, summary)
    write_trade_log(output_dir, trade_log)


@app.command("analyze-recording")
def analyze_recording(
    config_path: Path = typer.Option(..., "--config-path"),
    run_dir: Path = typer.Option(..., "--run-dir"),
    output_dir: Path = typer.Option(..., "--output-dir"),
) -> None:
    """Analyze recorded order books for market quality and selection."""
    settings = load_settings(config_path)
    store = JsonlEventStore(run_dir)
    try:
        store.validate_replay_inputs()
    except ReplayInputError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
    report = analyze_recorded_opportunities(
        catalog=store.read_catalog(required=True),
        events=list(store.iter_events(required=True)),
        stale_after_ms=settings.strategy.stale_after_ms,
        fee_rate=settings.strategy.fee_rate,
        slippage_buffer=settings.strategy.slippage_buffer,
        operational_buffer=settings.strategy.operational_buffer,
        research=settings.research,
    )
    write_market_quality_summary(
        output_dir,
        build_market_quality_summary_payload(
            report,
            config_path=config_path,
            thresholds=settings.research.model_dump(),
        ),
    )
    write_market_quality_by_market(
        output_dir,
        build_market_quality_by_market_payload(report),
    )


if __name__ == "__main__":
    app()
