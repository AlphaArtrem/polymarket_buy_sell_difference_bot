import json
from pathlib import Path

from polymarket_arb.catalog.service import build_catalog


def test_build_catalog_returns_binary_market_entry() -> None:
    payload = [json.loads(Path("tests/fixtures/gamma/market_binary.json").read_text())]

    catalog = build_catalog(payload, allowlist_caps={"will-btc-be-above-100k": 50.0})

    assert len(catalog) == 1
    assert catalog[0].slug == "will-btc-be-above-100k"
    assert catalog[0].yes_token_id
    assert catalog[0].no_token_id
    assert catalog[0].max_capital_usd == 50.0
