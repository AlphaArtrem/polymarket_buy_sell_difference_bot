import json
from typing import Any, Dict, List

from polymarket_arb.clients.gamma import GammaClient
from polymarket_arb.config import MarketSelection
from polymarket_arb.domain.models import MarketCatalogEntry


def build_catalog(
    markets: List[dict[str, Any]], allowlist_caps: Dict[str, float]
) -> List[MarketCatalogEntry]:
    entries: List[MarketCatalogEntry] = []
    for market in markets:
        slug = market.get("slug")
        if slug not in allowlist_caps:
            continue
        if not market.get("active") or market.get("closed"):
            continue
        token_pair = resolve_binary_token_pair(market)
        if token_pair is None:
            continue
        entries.append(
            MarketCatalogEntry(
                market_id=str(market["id"]),
                slug=str(slug),
                question=str(market.get("question") or slug),
                yes_token_id=token_pair[0],
                no_token_id=token_pair[1],
                fees_enabled=bool(market.get("feesEnabled", False)),
                max_capital_usd=allowlist_caps[str(slug)],
                active=True,
            )
        )
    return entries


def refresh_catalog(
    *, gamma_client: GammaClient, selections: list[MarketSelection]
) -> list[MarketCatalogEntry]:
    allowlist_caps = {
        selection.slug: selection.max_capital_usd for selection in selections
    }
    markets = gamma_client.fetch_markets_by_slugs(list(allowlist_caps))
    return build_catalog(markets, allowlist_caps=allowlist_caps)


def resolve_binary_token_pair(market: dict[str, Any]) -> tuple[str, str] | None:
    outcomes = coerce_string_list(market.get("outcomes", []))
    token_ids = coerce_string_list(market.get("clobTokenIds", []))
    if len(outcomes) != 2 or len(token_ids) != 2:
        return None
    normalized_outcomes = [outcome.strip().lower() for outcome in outcomes]
    if "yes" not in normalized_outcomes or "no" not in normalized_outcomes:
        return None
    yes_index = normalized_outcomes.index("yes")
    no_index = normalized_outcomes.index("no")
    return token_ids[yes_index], token_ids[no_index]


def coerce_string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return [value]
        if isinstance(parsed, list):
            return [str(item) for item in parsed]
    return []
