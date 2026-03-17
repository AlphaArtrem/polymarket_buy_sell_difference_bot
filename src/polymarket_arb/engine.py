from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any, Iterable, Optional

from polymarket_arb.portfolio.ledger import PortfolioLedger
from polymarket_arb.sim.execution import simulate_strict_pair_fill
from polymarket_arb.state.store import MarketStateStore
from polymarket_arb.strategy.opportunity import evaluate_opportunity
from polymarket_arb.strategy.sizing import compute_paired_size
from polymarket_arb.config import Settings
from polymarket_arb.domain.models import MarketCatalogEntry


@dataclass
class EngineOutcome:
    decision: str
    fill: Optional[object] = None
    rejection_reason: Optional[str] = None


class TradingEngine:
    def __init__(
        self,
        *,
        state_store: MarketStateStore,
        ledger: PortfolioLedger,
        settings: Any,
        market_caps_by_id: dict[str, float],
    ) -> None:
        self._state_store = state_store
        self._ledger = ledger
        self._settings = settings
        self._market_caps_by_id = market_caps_by_id

    @classmethod
    def from_defaults(
        cls,
        *,
        starting_cash_usd: float,
        per_market_cap_usd: float = 50.0,
        stale_after_ms: int = 5_000,
    ) -> "TradingEngine":
        settings = SimpleNamespace(
            strategy=SimpleNamespace(
                raw_alert_threshold=0.99,
                fee_rate=0.01,
                slippage_buffer=0.005,
                operational_buffer=0.005,
            ),
            portfolio=SimpleNamespace(max_total_deployed_usd=starting_cash_usd),
        )
        return cls(
            state_store=MarketStateStore(stale_after_ms=stale_after_ms),
            ledger=PortfolioLedger(
                starting_cash_usd=starting_cash_usd,
                free_cash_usd=starting_cash_usd,
            ),
            settings=settings,
            market_caps_by_id={"market-1": per_market_cap_usd},
        )

    @classmethod
    def from_settings(
        cls, settings: Settings, catalog: list[MarketCatalogEntry]
    ) -> "TradingEngine":
        market_caps_by_id = {
            entry.market_id: entry.max_capital_usd for entry in catalog
        } or {
            "market-1": settings.markets[0].max_capital_usd
        }
        return cls(
            state_store=MarketStateStore(
                stale_after_ms=settings.strategy.stale_after_ms
            ),
            ledger=PortfolioLedger(
                starting_cash_usd=settings.portfolio.starting_cash_usd,
                free_cash_usd=settings.portfolio.starting_cash_usd,
            ),
            settings=settings,
            market_caps_by_id=market_caps_by_id,
        )

    def on_event(self, event: Any) -> EngineOutcome:
        self._state_store.apply(event)
        try:
            paired = self._state_store.get_paired_book(event.market_id, event.timestamp_ms)
        except ValueError as exc:
            return EngineOutcome("reject", rejection_reason=str(exc))

        if not paired.yes_asks or not paired.no_asks:
            return EngineOutcome("reject", rejection_reason="missing_paired_book")

        decision = evaluate_opportunity(
            yes_ask=paired.yes_asks[0].price,
            no_ask=paired.no_asks[0].price,
            raw_alert_threshold=self._settings.strategy.raw_alert_threshold,
            fee_rate=self._settings.strategy.fee_rate,
            slippage_buffer=self._settings.strategy.slippage_buffer,
            operational_buffer=self._settings.strategy.operational_buffer,
        )
        if not decision.accepted:
            return EngineOutcome("reject", rejection_reason=decision.rejection_reason)

        size = compute_paired_size(
            yes_size=paired.yes_asks[0].size,
            no_size=paired.no_asks[0].size,
            available_cash=self._ledger.free_cash_usd,
            per_market_cap_usd=self._market_caps_by_id[event.market_id],
            remaining_deployable_usd=(
                self._settings.portfolio.max_total_deployed_usd
                - self._ledger.locked_cost_basis_usd
            ),
            estimated_net_cost=decision.estimated_net_cost,
        )
        if size <= 0:
            return EngineOutcome("reject", rejection_reason="size_limited_to_zero")

        fill = simulate_strict_pair_fill(
            yes_asks=paired.yes_asks,
            no_asks=paired.no_asks,
            target_size=size,
        )
        if fill.status != "filled":
            return EngineOutcome("reject", rejection_reason="broken_pair_execution")

        self._ledger.open_pair(fill.total_cost)
        return EngineOutcome("trade", fill=fill)

    def run(self, events: Iterable[Any]) -> dict[str, float]:
        trades = 0
        rejections = 0
        for event in events:
            outcome = self.on_event(event)
            if outcome.decision == "trade":
                trades += 1
            else:
                rejections += 1
        return {
            "trades": trades,
            "rejections": rejections,
            "realized_pnl_usd": self._ledger.realized_pnl_usd,
        }
