import json
from pathlib import Path

import httpx

from polymarket_arb.clients.gamma import GammaClient


def test_fetch_markets_by_slugs_queries_markets_endpoint_for_each_slug() -> None:
    payload_by_slug = {
        market["slug"]: market
        for market in json.loads(
            Path("tests/fixtures/gamma/markets_list.json").read_text(encoding="utf-8")
        )
    }
    seen_requests: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        slug = request.url.params["slug"]
        seen_requests.append((request.url.path, slug))
        return httpx.Response(200, json=[payload_by_slug[slug]])

    client = GammaClient(
        client=httpx.Client(
            base_url="https://gamma-api.polymarket.com",
            transport=httpx.MockTransport(handler),
        )
    )

    markets = client.fetch_markets_by_slugs(
        ["will-btc-be-above-100k", "multi-outcome-market"]
    )

    assert [market["slug"] for market in markets] == [
        "will-btc-be-above-100k",
        "multi-outcome-market",
    ]
    assert seen_requests == [
        ("/markets", "will-btc-be-above-100k"),
        ("/markets", "multi-outcome-market"),
    ]


def test_fetch_markets_by_slugs_skips_missing_slug_results() -> None:
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

    client = GammaClient(
        client=httpx.Client(
            base_url="https://gamma-api.polymarket.com",
            transport=httpx.MockTransport(handler),
        )
    )

    markets = client.fetch_markets_by_slugs(
        ["will-btc-be-above-100k", "missing-market"]
    )

    assert [market["slug"] for market in markets] == ["will-btc-be-above-100k"]
