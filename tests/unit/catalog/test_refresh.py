import json
from pathlib import Path

import httpx

from polymarket_arb.catalog.service import refresh_catalog
from polymarket_arb.clients.gamma import GammaClient
from polymarket_arb.config import MarketSelection


def test_refresh_catalog_filters_gamma_results_to_curated_binary_markets() -> None:
    payload_by_slug = {
        market["slug"]: market
        for market in json.loads(
            Path("tests/fixtures/gamma/markets_list.json").read_text(encoding="utf-8")
        )
    }

    def handler(request: httpx.Request) -> httpx.Response:
        slug = request.url.path.rsplit("/", 1)[-1]
        return httpx.Response(200, json=payload_by_slug[slug])

    gamma_client = GammaClient(
        client=httpx.Client(
            base_url="https://gamma-api.polymarket.com",
            transport=httpx.MockTransport(handler),
        )
    )

    catalog = refresh_catalog(
        gamma_client=gamma_client,
        selections=[
            MarketSelection(slug="will-btc-be-above-100k", max_capital_usd=50.0),
            MarketSelection(slug="multi-outcome-market", max_capital_usd=25.0),
        ],
    )

    assert len(catalog) == 1
    assert catalog[0].slug == "will-btc-be-above-100k"
    assert catalog[0].market_id == "0xabc"
    assert catalog[0].yes_token_id == "yes-token-abc"
    assert catalog[0].no_token_id == "no-token-abc"
