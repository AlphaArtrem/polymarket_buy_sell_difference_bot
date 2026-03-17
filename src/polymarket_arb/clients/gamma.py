from typing import Any

import httpx


class GammaClient:
    def __init__(
        self,
        base_url: str = "https://gamma-api.polymarket.com",
        *,
        client: httpx.Client | None = None,
    ) -> None:
        self._client = client or httpx.Client(base_url=base_url, timeout=10.0)

    def fetch_market_by_slug(self, slug: str) -> dict[str, Any]:
        response = self._client.get(f"/markets/slug/{slug}")
        response.raise_for_status()
        return response.json()

    def fetch_markets_by_slugs(self, slugs: list[str]) -> list[dict[str, Any]]:
        return [self.fetch_market_by_slug(slug) for slug in slugs]
