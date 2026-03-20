import json
from pathlib import Path

from polymarket_arb.catalog.service import build_candidate_catalog, build_catalog


def test_build_catalog_returns_binary_market_entry() -> None:
    payload = [json.loads(Path("tests/fixtures/gamma/market_binary.json").read_text())]

    catalog = build_catalog(payload, allowlist_caps={"will-btc-be-above-100k": 50.0})

    assert len(catalog) == 1
    assert catalog[0].slug == "will-btc-be-above-100k"
    assert catalog[0].yes_token_id
    assert catalog[0].no_token_id
    assert catalog[0].max_capital_usd == 50.0


def test_build_candidate_catalog_preserves_resolution_text_and_tags() -> None:
    payload = [
        {
            "id": "123",
            "slug": "will-example-happen",
            "question": "Will example happen?",
            "active": True,
            "closed": False,
            "outcomes": ["Yes", "No"],
            "clobTokenIds": ["yes-1", "no-1"],
            "description": "Resolves to YES if Example API says true.",
            "category": "crypto",
            "endDate": "2026-04-01T00:00:00Z",
        }
    ]

    catalog = build_candidate_catalog(payload)

    assert catalog[0].resolution_text == "Resolves to YES if Example API says true."
    assert "objective_source_candidate" in catalog[0].tags
