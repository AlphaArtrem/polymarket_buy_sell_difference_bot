from pydantic import BaseModel

from polymarket_arb.domain.models import BookLevel, DirectionalFillRecord, EventPaperRejectionRecord
from polymarket_arb.portfolio.directional import DirectionalLedger
from polymarket_arb.portfolio.event_lifecycle import decide_exit_action
from polymarket_arb.sim.directional import simulate_directional_fill


class EventPaperTrade(BaseModel):
    trade_id: str
    market_id: str
    slug: str
    direction: str
    size: float
    entry_price: float
    expected_edge_bps: float
    timestamp_ms: int
    exit_mode: str


class EventPaperOutcome(BaseModel):
    decision: str
    reason: str | None = None
    trade: EventPaperTrade | None = None


class EventPaperRunner:
    def __init__(
        self,
        *,
        starting_cash_usd: float,
        max_total_deployed_usd: float,
        default_exit_mode: str,
        repricing_target_bps: float = 50,
        max_holding_seconds: int = 900,
        entry_slippage_buffer: float = 0.0,
        exit_slippage_buffer: float = 0.01,
        allow_hold_to_resolution: bool = False,
    ) -> None:
        self.ledger = DirectionalLedger(starting_cash_usd=starting_cash_usd)
        self.max_total_deployed_usd = max_total_deployed_usd
        self.default_exit_mode = default_exit_mode
        self.repricing_target_bps = repricing_target_bps
        self.max_holding_seconds = max_holding_seconds
        self.entry_slippage_buffer = entry_slippage_buffer
        self.exit_slippage_buffer = exit_slippage_buffer
        self.allow_hold_to_resolution = allow_hold_to_resolution
        self.trade_log: list[EventPaperTrade] = []
        self.rejection_log: list[EventPaperRejectionRecord] = []
        self.exit_log: list[DirectionalFillRecord] = []
        self._trade_by_id: dict[str, EventPaperTrade] = {}

    def on_signal(
        self,
        *,
        market_id: str,
        slug: str,
        direction: str,
        expected_edge_bps: float,
        asks: list[BookLevel],
        bids: list[BookLevel],
        timestamp_ms: int,
    ) -> EventPaperOutcome:
        del bids

        if expected_edge_bps <= 0:
            return self._reject(
                market_id=market_id,
                slug=slug,
                timestamp_ms=timestamp_ms,
                reason="edge_below_threshold",
            )
        if not asks:
            return self._reject(
                market_id=market_id,
                slug=slug,
                timestamp_ms=timestamp_ms,
                reason="entry_no_fill",
            )

        remaining_deployment = (
            self.max_total_deployed_usd - self.ledger.deployed_cost_basis_usd
        )
        if remaining_deployment <= 0:
            return self._reject(
                market_id=market_id,
                slug=slug,
                timestamp_ms=timestamp_ms,
                reason="deployment_limit_reached",
            )

        best_ask = asks[0].price
        affordable_size = min(
            sum(level.size for level in asks),
            self.ledger.free_cash_usd / best_ask,
            remaining_deployment / best_ask,
        )
        if affordable_size <= 0:
            return self._reject(
                market_id=market_id,
                slug=slug,
                timestamp_ms=timestamp_ms,
                reason="insufficient_cash",
            )

        entry_fill = simulate_directional_fill(
            side="buy",
            book_levels=asks,
            requested_size=affordable_size,
            slippage_buffer=self.entry_slippage_buffer,
            market_id=market_id,
            direction=direction,
            exit_mode=self.default_exit_mode,
        )
        if entry_fill.filled_size <= 0:
            return self._reject(
                market_id=market_id,
                slug=slug,
                timestamp_ms=timestamp_ms,
                reason="entry_no_fill",
            )

        trade_id = self.ledger.open_position(
            market_id=market_id,
            direction=direction,
            size=entry_fill.filled_size,
            entry_price=entry_fill.average_price,
        )
        trade = EventPaperTrade(
            trade_id=trade_id,
            market_id=market_id,
            slug=slug,
            direction=direction,
            size=entry_fill.filled_size,
            entry_price=entry_fill.average_price,
            expected_edge_bps=expected_edge_bps,
            timestamp_ms=timestamp_ms,
            exit_mode=self.default_exit_mode,
        )
        self.trade_log.append(trade)
        self._trade_by_id[trade_id] = trade
        return EventPaperOutcome(decision="trade", trade=trade)

    def evaluate_open_position(
        self,
        *,
        trade_id: str,
        market_id: str,
        bids: list[BookLevel],
        current_timestamp_ms: int,
        terminal_signal: bool,
    ) -> EventPaperOutcome:
        trade = self._trade_by_id[trade_id]
        position = next(
            position for position in self.ledger.open_positions() if position.trade_id == trade_id
        )
        current_price = bids[0].price if bids else 0.0
        action = decide_exit_action(
            exit_mode=trade.exit_mode,
            entry_price=position.entry_price,
            current_price=current_price,
            repricing_target_bps=self.repricing_target_bps,
            elapsed_seconds=max(0, (current_timestamp_ms - trade.timestamp_ms) // 1000),
            max_holding_seconds=self.max_holding_seconds,
            terminal_signal=terminal_signal,
            allow_hold_to_resolution=self.allow_hold_to_resolution,
        )
        if action != "exit_now":
            return EventPaperOutcome(decision="hold", reason=action)

        exit_fill = simulate_directional_fill(
            side="sell",
            book_levels=bids,
            requested_size=position.size,
            slippage_buffer=self.exit_slippage_buffer,
            market_id=market_id,
            direction=position.direction,
            exit_mode=trade.exit_mode,
        )
        self.exit_log.append(exit_fill)
        if exit_fill.filled_size <= 0:
            return EventPaperOutcome(decision="hold", reason="exit_no_fill")
        self.ledger.close_position(
            trade_id=trade_id,
            exit_price=exit_fill.average_price,
            close_size=exit_fill.filled_size,
        )
        return EventPaperOutcome(decision="exit", reason=exit_fill.status, trade=trade)

    def _reject(
        self,
        *,
        market_id: str,
        slug: str,
        timestamp_ms: int,
        reason: str,
    ) -> EventPaperOutcome:
        self.rejection_log.append(
            EventPaperRejectionRecord(
                market_id=market_id,
                slug=slug,
                timestamp_ms=timestamp_ms,
                reason=reason,
            )
        )
        return EventPaperOutcome(decision="reject", reason=reason)
