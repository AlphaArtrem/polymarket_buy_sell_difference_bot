from pathlib import Path
from typing import List

import typer

from polymarket_arb.adapters.live import LiveAdapter
from polymarket_arb.catalog.service import refresh_catalog as refresh_catalog_service
from polymarket_arb.clients.clob import ClobClient
from polymarket_arb.clients.clob import ClobWebSocketClient
from polymarket_arb.clients.gamma import GammaClient
from polymarket_arb.recording.recorder import Recorder
from polymarket_arb.config import Settings, load_settings
from polymarket_arb.domain.models import MarketCatalogEntry
from polymarket_arb.engine import TradingEngine
from polymarket_arb.ops.latency import measure_http_endpoint, measure_websocket_connect
from polymarket_arb.recording.storage import JsonlEventStore, ReplayInputError
from polymarket_arb.adapters.replay import ReplayAdapter
from polymarket_arb.research.opportunities import analyze_recorded_opportunities
from polymarket_arb.reporting.writers import (
    write_catalog_snapshot,
    write_feed_health,
    write_latency_summary,
    write_opportunity_summary,
    write_run_summary,
)

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
                "asset_ids": [first_market.yes_token_id, first_market.no_token_id],
                "type": "market",
            },
            samples=samples,
        ),
    }
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


@app.command("analyze-recording")
def analyze_recording(
    config_path: Path = typer.Option(..., "--config-path"),
    run_dir: Path = typer.Option(..., "--run-dir"),
    output_dir: Path = typer.Option(..., "--output-dir"),
) -> None:
    """Analyze recorded order books for full-set opportunity frequency."""
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
    )
    write_opportunity_summary(output_dir, report)


if __name__ == "__main__":
    app()
