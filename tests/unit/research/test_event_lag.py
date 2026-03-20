from polymarket_arb.domain.models import SourceEventRecord
from polymarket_arb.research.event_lag import EventLagTracker


def test_event_lag_tracker_computes_first_move_and_best_entry() -> None:
    tracker = EventLagTracker(response_window_seconds=120, min_expected_edge_bps=25)
    tracker.observe_source_event(
        SourceEventRecord(
            source_event_id="source-1",
            source_type="http_json",
            source_key="sec-filing",
            received_timestamp_ms=1_700_000_000_000,
            normalized_payload={"status": "filed"},
            affected_market_ids=["123"],
        )
    )
    tracker.observe_market_snapshot(
        market_id="123",
        timestamp_ms=1_700_000_005_000,
        best_yes_ask=0.42,
        best_no_ask=0.60,
        yes_size=50,
        no_size=40,
    )

    summary = tracker.finalize_market("123")

    assert summary.time_to_first_move_ms == 5_000
    assert summary.best_entry_edge_bps > 0
