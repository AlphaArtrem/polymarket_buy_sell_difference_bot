# Polymarket Arb

Beginner-first Polymarket full-set arbitrage tooling for recording market data, replaying it, and running live paper-trading experiments.

## Local Development

```bash
python3 -m venv .venv
.venv/bin/python -m pip install httpx pydantic PyYAML typer websockets pytest pytest-asyncio
PYTHONPATH=src .venv/bin/pytest -v
PYTHONPATH=src .venv/bin/python -m polymarket_arb.cli catalog-refresh --config-path configs/markets.sample.yaml --output-path artifacts/catalog.json
PYTHONPATH=src .venv/bin/python -m polymarket_arb.cli bench-latency --config-path configs/markets.sample.yaml --output-path artifacts/runtime/latency.json --samples 5
PYTHONPATH=src .venv/bin/python -m polymarket_arb.cli record-live --config-path configs/markets.sample.yaml --run-dir artifacts/live-capture --duration-seconds 10 --mode stream
PYTHONPATH=src .venv/bin/python -m polymarket_arb.cli run-paper --config-path configs/markets.sample.yaml --output-dir artifacts/paper-report --duration-seconds 10 --mode stream
PYTHONPATH=src .venv/bin/python -m polymarket_arb.cli run-replay --config-path configs/markets.sample.yaml --run-dir artifacts/demo-run --output-dir artifacts/demo-report
```

## VPS Workflow

1. Benchmark each candidate VPS with `bench-latency` using the same config you plan to trade with.
2. Pick the lowest-latency region that can reach Gamma, CLOB REST, the CLOB market WebSocket, and your Polygon RPC cleanly.
3. Run `run-paper --mode stream` first and inspect `summary.json` plus `feed_health.json`.
4. Keep authenticated trading out of scope until the paper path is stable and later phases are complete.

The sample config now includes `api.market_ws_url` and `runtime.mode` so the same file can drive polling fallback locally and streaming mode on the VPS.
