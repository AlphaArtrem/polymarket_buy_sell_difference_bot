# Polymarket Arb

Beginner-first Polymarket full-set arbitrage tooling for recording market data, replaying it, and running live paper-trading experiments.

## Local Development

```bash
python3 -m venv .venv
.venv/bin/python -m pip install httpx pydantic PyYAML typer websockets pytest pytest-asyncio
PYTHONPATH=src .venv/bin/pytest -v
PYTHONPATH=src .venv/bin/python -m polymarket_arb.cli catalog-refresh --config-path configs/markets.sample.yaml --output-path artifacts/catalog.json
PYTHONPATH=src .venv/bin/python -m polymarket_arb.cli record-live --config-path configs/markets.sample.yaml --run-dir artifacts/live-capture --duration-seconds 10
PYTHONPATH=src .venv/bin/python -m polymarket_arb.cli run-paper --config-path configs/markets.sample.yaml --output-dir artifacts/paper-report --duration-seconds 10
PYTHONPATH=src .venv/bin/python -m polymarket_arb.cli run-replay --config-path configs/markets.sample.yaml --run-dir artifacts/demo-run --output-dir artifacts/demo-report
```
