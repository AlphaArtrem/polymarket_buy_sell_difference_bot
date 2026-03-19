import math
from dataclasses import dataclass, field

from pydantic import BaseModel, Field

from polymarket_arb.config import ResearchSettings
from polymarket_arb.domain.events import OrderBookEvent
from polymarket_arb.domain.models import MarketCatalogEntry
from polymarket_arb.state.store import MarketStateStore


class MarketQualityRecord(BaseModel):
    market_id: str
    slug: str
    question: str
    message_count: int = 0
    paired_snapshot_count: int = 0
    stale_snapshot_count: int = 0
    raw_opportunity_count: int = 0
    post_cost_opportunity_count: int = 0
    raw_opportunities_per_minute: float = 0.0
    post_cost_opportunities_per_minute: float = 0.0
    snapshots_per_minute: float = 0.0
    best_raw_sum: float | None = None
    best_net_sum: float | None = None
    best_net_edge_bps: float = 0.0
    opportunity_window_count: int = 0
    total_time_in_edge_ms: int = 0
    edge_time_share: float = 0.0
    p50_window_ms: float = 0.0
    p95_window_ms: float = 0.0
    max_window_ms: float = 0.0
    status: str = "drop"
    reasons: list[str] = Field(default_factory=list)


class MarketQualityReport(BaseModel):
    event_count: int
    paired_snapshot_count: int
    raw_opportunity_count: int
    post_cost_opportunity_count: int
    opportunity_window_count: int
    run_duration_seconds: float
    stream_message_count: int = 0
    classification_counts: dict[str, int] = Field(default_factory=dict)
    markets: list[MarketQualityRecord]


@dataclass
class _TrackerState:
    active_window_start_ms: int | None = None
    window_durations_ms: list[int] = field(default_factory=list)
    last_event_ms: int = 0


class MarketQualityTracker:
    def __init__(
        self,
        *,
        catalog: list[MarketCatalogEntry],
        stale_after_ms: int,
        fee_rate: float,
        slippage_buffer: float,
        operational_buffer: float,
        research: ResearchSettings | None = None,
    ) -> None:
        self._state_store = MarketStateStore(stale_after_ms=stale_after_ms)
        self._fee_rate = fee_rate
        self._slippage_buffer = slippage_buffer
        self._operational_buffer = operational_buffer
        self._research = research or ResearchSettings()
        self._records = {
            entry.market_id: MarketQualityRecord(
                market_id=entry.market_id,
                slug=entry.slug,
                question=entry.question,
            )
            for entry in catalog
        }
        self._tracker_states = {
            entry.market_id: _TrackerState() for entry in catalog
        }
        self._event_count = 0
        self._paired_snapshot_count = 0
        self._raw_opportunity_count = 0
        self._post_cost_opportunity_count = 0
        self._stream_message_count = 0

    def note_stream_message(self, count: int = 1) -> None:
        self._stream_message_count += count

    def observe(self, event: OrderBookEvent) -> None:
        self._event_count += 1
        self._state_store.apply(event)

        record = self._records.get(event.market_id)
        tracker_state = self._tracker_states.get(event.market_id)
        if record is None or tracker_state is None:
            return

        record.message_count += 1
        tracker_state.last_event_ms = max(tracker_state.last_event_ms, event.timestamp_ms)

        try:
            paired = self._state_store.get_paired_book(event.market_id, event.timestamp_ms)
        except (KeyError, ValueError):
            record.stale_snapshot_count += 1
            self._close_window(event.market_id, event.timestamp_ms)
            return

        if not paired.yes_asks or not paired.no_asks:
            self._close_window(event.market_id, event.timestamp_ms)
            return

        raw_sum = min(level.price for level in paired.yes_asks) + min(
            level.price for level in paired.no_asks
        )
        net_sum = raw_sum + self._fee_rate + self._slippage_buffer + self._operational_buffer

        self._paired_snapshot_count += 1
        record.paired_snapshot_count += 1
        record.best_raw_sum = _min_value(record.best_raw_sum, raw_sum)
        record.best_net_sum = _min_value(record.best_net_sum, net_sum)
        record.best_net_edge_bps = max(record.best_net_edge_bps, net_edge_bps(net_sum))

        if raw_sum < 1.0:
            self._raw_opportunity_count += 1
            record.raw_opportunity_count += 1

        if net_sum < 1.0:
            self._post_cost_opportunity_count += 1
            record.post_cost_opportunity_count += 1
            self._open_or_extend_window(event.market_id, event.timestamp_ms)
            return

        self._close_window(event.market_id, event.timestamp_ms)

    def finalize(self, *, run_duration_seconds: float) -> MarketQualityReport:
        run_duration_seconds = max(run_duration_seconds, 0.0)
        run_duration_ms = int(run_duration_seconds * 1000)
        for market_id, tracker_state in self._tracker_states.items():
            if tracker_state.active_window_start_ms is not None:
                self._close_window(market_id, tracker_state.last_event_ms)

        classification_counts = {"keep": 0, "watch": 0, "drop": 0}
        markets = list(self._records.values())
        for record in markets:
            self._finalize_record(record, run_duration_seconds, run_duration_ms)
            classification_counts[record.status] = (
                classification_counts.get(record.status, 0) + 1
            )

        return MarketQualityReport(
            event_count=self._event_count,
            paired_snapshot_count=self._paired_snapshot_count,
            raw_opportunity_count=self._raw_opportunity_count,
            post_cost_opportunity_count=self._post_cost_opportunity_count,
            opportunity_window_count=sum(record.opportunity_window_count for record in markets),
            run_duration_seconds=run_duration_seconds,
            stream_message_count=self._stream_message_count,
            classification_counts=classification_counts,
            markets=markets,
        )

    def _open_or_extend_window(self, market_id: str, timestamp_ms: int) -> None:
        tracker_state = self._tracker_states[market_id]
        if tracker_state.active_window_start_ms is None:
            tracker_state.active_window_start_ms = timestamp_ms

    def _close_window(self, market_id: str, timestamp_ms: int) -> None:
        tracker_state = self._tracker_states[market_id]
        if tracker_state.active_window_start_ms is None:
            return
        duration_ms = max(timestamp_ms - tracker_state.active_window_start_ms, 0)
        tracker_state.window_durations_ms.append(duration_ms)
        tracker_state.active_window_start_ms = None

    def _finalize_record(
        self,
        record: MarketQualityRecord,
        run_duration_seconds: float,
        run_duration_ms: int,
    ) -> None:
        minutes = run_duration_seconds / 60 if run_duration_seconds > 0 else 0.0
        durations = self._tracker_states[record.market_id].window_durations_ms
        duration_summary = summarize_window_durations(durations)

        record.opportunity_window_count = len(durations)
        record.total_time_in_edge_ms = int(sum(durations))
        record.p50_window_ms = duration_summary["p50_window_ms"]
        record.p95_window_ms = duration_summary["p95_window_ms"]
        record.max_window_ms = duration_summary["max_window_ms"]
        record.snapshots_per_minute = (
            record.paired_snapshot_count / minutes if minutes > 0 else 0.0
        )
        record.raw_opportunities_per_minute = (
            record.raw_opportunity_count / minutes if minutes > 0 else 0.0
        )
        record.post_cost_opportunities_per_minute = (
            record.post_cost_opportunity_count / minutes if minutes > 0 else 0.0
        )
        record.edge_time_share = (
            record.total_time_in_edge_ms / run_duration_ms if run_duration_ms > 0 else 0.0
        )

        status, reasons = classify_market_quality(record, self._research)
        record.status = status
        record.reasons = reasons


def summarize_window_durations(durations_ms: list[int]) -> dict[str, float]:
    if not durations_ms:
        return {
            "p50_window_ms": 0.0,
            "p95_window_ms": 0.0,
            "max_window_ms": 0.0,
        }

    ordered = sorted(float(value) for value in durations_ms)
    return {
        "p50_window_ms": _percentile(ordered, 0.50),
        "p95_window_ms": _percentile(ordered, 0.95),
        "max_window_ms": ordered[-1],
    }


def classify_market_quality(
    record: MarketQualityRecord, research: ResearchSettings
) -> tuple[str, list[str]]:
    if record.paired_snapshot_count < research.low_sample_paired_snapshot_floor:
        return "drop", ["too_quiet"]
    if record.post_cost_opportunity_count == 0:
        return "drop", ["no_post_cost_edge"]

    keep_checks = (
        record.snapshots_per_minute >= research.keep_min_paired_snapshots_per_minute,
        record.post_cost_opportunities_per_minute
        >= research.keep_min_post_cost_opportunities_per_minute,
        record.total_time_in_edge_ms >= research.keep_min_total_time_in_edge_ms,
        record.best_net_edge_bps >= research.keep_min_best_net_edge_bps,
        record.max_window_ms >= research.keep_min_max_window_ms,
    )
    if all(keep_checks):
        return "keep", ["passes_keep_thresholds"]

    watch_checks = (
        record.snapshots_per_minute >= research.watch_min_paired_snapshots_per_minute,
        record.post_cost_opportunities_per_minute
        >= research.watch_min_post_cost_opportunities_per_minute,
        record.best_net_edge_bps >= research.watch_min_best_net_edge_bps,
    )
    if all(watch_checks):
        return "watch", ["passes_watch_thresholds"]

    reasons: list[str] = []
    if record.best_net_edge_bps < research.watch_min_best_net_edge_bps:
        reasons.append("edge_too_small")
    if record.snapshots_per_minute < research.watch_min_paired_snapshots_per_minute:
        reasons.append("too_quiet")
    if (
        record.post_cost_opportunities_per_minute
        < research.watch_min_post_cost_opportunities_per_minute
        or record.total_time_in_edge_ms < research.keep_min_total_time_in_edge_ms
        or record.max_window_ms < research.keep_min_max_window_ms
    ):
        reasons.append("edge_too_brief")
    return "drop", reasons or ["edge_too_brief"]


def net_edge_bps(best_net_sum: float | None) -> float:
    if best_net_sum is None or best_net_sum >= 1.0:
        return 0.0
    return round((1.0 - best_net_sum) * 10_000, 4)


def _min_value(current: float | None, candidate: float) -> float:
    if current is None:
        return candidate
    return min(current, candidate)


def _percentile(samples: list[float], quantile: float) -> float:
    if not samples:
        return 0.0
    index = max(math.ceil(len(samples) * quantile) - 1, 0)
    return samples[index]
