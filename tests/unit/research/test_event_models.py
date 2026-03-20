from polymarket_arb.domain.models import EnrichedMarketEntry, SourceEventRecord


def test_source_event_record_keeps_source_and_market_links() -> None:
    event = SourceEventRecord(
        source_event_id="source-1",
        source_type="http_json",
        source_key="sec-filing",
        received_timestamp_ms=1_700_000_000_000,
        normalized_payload={"headline": "Form filed"},
        affected_market_ids=["123"],
    )

    assert event.source_key == "sec-filing"
    assert event.affected_market_ids == ["123"]
