from dataclasses import dataclass


@dataclass
class PortfolioLedger:
    starting_cash_usd: float
    free_cash_usd: float
    locked_cost_basis_usd: float = 0.0
    realized_pnl_usd: float = 0.0

    def open_pair(self, total_cost: float) -> None:
        self.free_cash_usd -= total_cost
        self.locked_cost_basis_usd += total_cost

    def resolve_pair(self, *, total_cost: float, payout: float) -> None:
        self.locked_cost_basis_usd -= total_cost
        self.free_cash_usd += payout
        self.realized_pnl_usd += payout - total_cost
