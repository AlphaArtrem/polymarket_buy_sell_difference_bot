def compute_paired_size(
    *,
    yes_size: float,
    no_size: float,
    available_cash: float,
    per_market_cap_usd: float,
    remaining_deployable_usd: float,
    estimated_net_cost: float,
) -> float:
    paired_depth = min(yes_size, no_size)
    cash_limited = available_cash / estimated_net_cost
    market_cap_limited = per_market_cap_usd / estimated_net_cost
    portfolio_limited = remaining_deployable_usd / estimated_net_cost
    return max(
        0.0,
        min(paired_depth, cash_limited, market_cap_limited, portfolio_limited),
    )
