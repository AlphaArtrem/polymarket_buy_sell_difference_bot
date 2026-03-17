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
        slug = request.url.params["slug"]
        payload = [payload_by_slug[slug]] if slug in payload_by_slug else []
        return httpx.Response(200, json=payload)

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


def test_refresh_catalog_ignores_stale_allowlist_slugs() -> None:
    payload_by_slug = {
        market["slug"]: market
        for market in json.loads(
            Path("tests/fixtures/gamma/markets_list.json").read_text(encoding="utf-8")
        )
    }

    def handler(request: httpx.Request) -> httpx.Response:
        slug = request.url.params["slug"]
        payload = [payload_by_slug[slug]] if slug in payload_by_slug else []
        return httpx.Response(200, json=payload)

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
            MarketSelection(slug="missing-market", max_capital_usd=25.0),
        ],
    )

    assert [entry.slug for entry in catalog] == ["will-btc-be-above-100k"]
