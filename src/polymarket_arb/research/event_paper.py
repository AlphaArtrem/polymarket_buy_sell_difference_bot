from pydantic import BaseModel

from polymarket_arb.portfolio.directional import DirectionalLedger


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
    ) -> None:
        self.ledger = DirectionalLedger(starting_cash_usd=starting_cash_usd)
        self.max_total_deployed_usd = max_total_deployed_usd
        self.default_exit_mode = default_exit_mode
        self.trade_log: list[EventPaperTrade] = []

    def on_signal(
        self,
        *,
        market_id: str,
        slug: str,
        direction: str,
        expected_edge_bps: float,
        best_ask: float,
        available_size: float,
        timestamp_ms: int,
    ) -> EventPaperOutcome:
        if expected_edge_bps <= 0:
            return EventPaperOutcome(decision="reject", reason="edge_below_threshold")
        if best_ask <= 0 or available_size <= 0:
            return EventPaperOutcome(decision="reject", reason="no_liquidity")

        remaining_deployment = (
            self.max_total_deployed_usd - self.ledger.deployed_cost_basis_usd
        )
        if remaining_deployment <= 0:
            return EventPaperOutcome(decision="reject", reason="deployment_limit_reached")

        affordable_size = min(
            available_size,
            self.ledger.free_cash_usd / best_ask,
            remaining_deployment / best_ask,
        )
        if affordable_size <= 0:
            return EventPaperOutcome(decision="reject", reason="insufficient_cash")

        trade_id = self.ledger.open_position(
            market_id=market_id,
            direction=direction,
            size=affordable_size,
            entry_price=best_ask,
        )
        trade = EventPaperTrade(
            trade_id=trade_id,
            market_id=market_id,
            slug=slug,
            direction=direction,
            size=affordable_size,
            entry_price=best_ask,
            expected_edge_bps=expected_edge_bps,
            timestamp_ms=timestamp_ms,
            exit_mode=self.default_exit_mode,
        )
        self.trade_log.append(trade)
        return EventPaperOutcome(decision="trade", trade=trade)
