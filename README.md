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
PYTHONPATH=src .venv/bin/python -m polymarket_arb.cli study-live-opportunities --config-path configs/markets.research.yaml --output-dir artifacts/market-study --duration-seconds 300 --mode stream
PYTHONPATH=src .venv/bin/python -m polymarket_arb.cli analyze-recording --config-path configs/markets.research.yaml --run-dir artifacts/live-capture --output-dir artifacts/replay-study
PYTHONPATH=src .venv/bin/python -m polymarket_arb.cli run-paper --config-path configs/markets.sample.yaml --output-dir artifacts/paper-report --duration-seconds 10 --mode stream
PYTHONPATH=src .venv/bin/python -m polymarket_arb.cli run-replay --config-path configs/markets.sample.yaml --run-dir artifacts/demo-run --output-dir artifacts/demo-report
```

## VPS Workflow

1. Benchmark each candidate VPS with `bench-latency` using the same config you plan to trade with.
2. Pick the lowest-latency region that can reach Gamma, CLOB REST, the CLOB market WebSocket, and your Polygon RPC cleanly.
3. Run `study-live-opportunities --mode stream` first to classify markets as `keep`, `watch`, or `drop`.
4. Narrow the market universe using `market_quality_summary.json` and `market_quality_by_market.json`.
5. Run `run-paper --mode stream` only after the market universe is narrowed and inspect `summary.json` plus `feed_health.json`.
6. Keep authenticated trading out of scope until the paper path is stable and later phases are complete.

Phase 2.2 artifacts:

- `market_quality_summary.json`: run-level summary, classification counts, top markets, and thresholds used
- `market_quality_by_market.json`: per-market source of truth for activity, opportunity, persistence, and final `keep` / `watch` / `drop` status
- `feed_health.json`: transport-side counters from the live adapter when the study runs in stream mode

Interpret the market classes conservatively:

- `keep`: active enough, strong enough, and persistent enough to deserve deeper paper-trading and accounting work
- `watch`: shows some edge, but still misses one or more stricter `keep` thresholds
- `drop`: too quiet, no post-cost edge, or observed edge is too small or too brief

The sample configs now include `api.market_ws_url`, `runtime.mode`, and `research` thresholds so the same repo can support low-latency stream studies on the VPS and simpler local experimentation.
