from polymarket_arb.sources.adapters import normalize_http_json_payload
from polymarket_arb.sources.models import SourceDefinition


def test_normalize_http_json_payload_builds_source_event() -> None:
    definition = SourceDefinition(
        key="sec-filing",
        source_type="http_json",
        url="https://example.com/api",
        parser="sec_status",
        market_slugs=["will-example-happen"],
        implied_direction="yes",
    )

    event = normalize_http_json_payload(
        definition=definition,
        payload={"status": "filed", "timestamp": "2026-03-20T10:00:00Z"},
        received_timestamp_ms=1_742_468_400_000,
        affected_market_ids=["123"],
    )

    assert event.source_key == "sec-filing"
    assert event.normalized_payload["status"] == "filed"
