from pydantic import BaseModel

from polymarket_arb.domain.models import SourceEventRecord


class EventLagSummary(BaseModel):
    market_id: str
    source_event_id: str
    time_to_first_move_ms: int = 0
    best_entry_edge_bps: float = 0.0
    max_favorable_move_bps: float = 0.0


class EventLagTracker:
    def __init__(self, *, response_window_seconds: int, min_expected_edge_bps: float) -> None:
        self._response_window_ms = response_window_seconds * 1000
        self._min_expected_edge_bps = min_expected_edge_bps
        self._events_by_market: dict[str, SourceEventRecord] = {}
        self._summaries: dict[str, EventLagSummary] = {}

    def observe_source_event(self, event: SourceEventRecord) -> None:
        for market_id in event.affected_market_ids:
            self._events_by_market[market_id] = event
            self._summaries[market_id] = EventLagSummary(
                market_id=market_id,
                source_event_id=event.source_event_id,
            )

    def observe_market_snapshot(
        self,
        *,
        market_id: str,
        timestamp_ms: int,
        best_yes_ask: float,
        best_no_ask: float,
        yes_size: float,
        no_size: float,
    ) -> None:
        event = self._events_by_market.get(market_id)
        summary = self._summaries.get(market_id)
        if event is None or summary is None:
            return
        lag_ms = timestamp_ms - event.received_timestamp_ms
        if lag_ms < 0 or lag_ms > self._response_window_ms:
            return
        if summary.time_to_first_move_ms == 0:
            summary.time_to_first_move_ms = lag_ms
        edge_bps = self._compute_entry_edge_bps(
            best_yes_ask=best_yes_ask,
            best_no_ask=best_no_ask,
            yes_size=yes_size,
            no_size=no_size,
        )
        if edge_bps < self._min_expected_edge_bps:
            return
        summary.best_entry_edge_bps = max(summary.best_entry_edge_bps, edge_bps)
        summary.max_favorable_move_bps = max(summary.max_favorable_move_bps, edge_bps)

    def finalize_market(self, market_id: str) -> EventLagSummary:
        summary = self._summaries.get(market_id)
        if summary is not None:
            return summary
        return EventLagSummary(market_id=market_id, source_event_id="")

    def _compute_entry_edge_bps(
        self,
        *,
        best_yes_ask: float,
        best_no_ask: float,
        yes_size: float,
        no_size: float,
    ) -> float:
        candidate_edges: list[float] = []
        if yes_size > 0:
            candidate_edges.append(max(0.0, (1.0 - best_yes_ask) * 10_000))
        if no_size > 0:
            candidate_edges.append(max(0.0, (1.0 - best_no_ask) * 10_000))
        if not candidate_edges:
            return 0.0
        return max(candidate_edges)
