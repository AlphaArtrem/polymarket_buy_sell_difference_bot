from dataclasses import dataclass


@dataclass
class DirectionalPosition:
    trade_id: str
    market_id: str
    direction: str
    size: float
    entry_price: float

    @property
    def cost_basis_usd(self) -> float:
        return self.size * self.entry_price


class DirectionalLedger:
    def __init__(self, *, starting_cash_usd: float) -> None:
        self.starting_cash_usd = starting_cash_usd
        self.free_cash_usd = starting_cash_usd
        self.realized_pnl_usd = 0.0
        self._next_trade_number = 1
        self._positions: dict[str, DirectionalPosition] = {}

    @property
    def deployed_cost_basis_usd(self) -> float:
        return sum(position.cost_basis_usd for position in self._positions.values())

    def open_position(
        self, *, market_id: str, direction: str, size: float, entry_price: float
    ) -> str:
        trade_id = f"trade-{self._next_trade_number}"
        self._next_trade_number += 1
        position = DirectionalPosition(
            trade_id=trade_id,
            market_id=market_id,
            direction=direction,
            size=size,
            entry_price=entry_price,
        )
        self.free_cash_usd = round(self.free_cash_usd - position.cost_basis_usd, 10)
        self._positions[trade_id] = position
        return trade_id

    def close_position(self, *, trade_id: str, exit_price: float) -> None:
        position = self._positions.pop(trade_id)
        exit_value = position.size * exit_price
        self.free_cash_usd = round(self.free_cash_usd + exit_value, 10)
        self.realized_pnl_usd = round(
            self.realized_pnl_usd + exit_value - position.cost_basis_usd,
            10,
        )
