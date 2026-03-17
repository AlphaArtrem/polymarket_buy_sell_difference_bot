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
        response = self._client.get("/markets", params={"slug": slug})
        response.raise_for_status()
        payload = response.json()
        if not payload:
            raise LookupError(f"No Gamma market found for slug '{slug}'")
        return payload[0]

    def fetch_markets_by_slugs(self, slugs: list[str]) -> list[dict[str, Any]]:
        markets: list[dict[str, Any]] = []
        for slug in slugs:
            try:
                markets.append(self.fetch_market_by_slug(slug))
            except LookupError:
                continue
        return markets
