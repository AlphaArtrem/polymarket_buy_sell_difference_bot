import json
from pathlib import Path

import httpx

from polymarket_arb.clients.gamma import GammaClient


def test_fetch_markets_by_slugs_requests_each_curated_slug() -> None:
    payload_by_slug = {
        market["slug"]: market
        for market in json.loads(
            Path("tests/fixtures/gamma/markets_list.json").read_text(encoding="utf-8")
        )
    }
    seen_paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_paths.append(request.url.path)
        slug = request.url.path.rsplit("/", 1)[-1]
        return httpx.Response(200, json=payload_by_slug[slug])

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
    assert seen_paths == [
        "/markets/slug/will-btc-be-above-100k",
        "/markets/slug/multi-outcome-market",
    ]
