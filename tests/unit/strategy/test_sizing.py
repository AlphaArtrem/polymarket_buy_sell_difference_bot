from polymarket_arb.strategy.sizing import compute_paired_size


def test_compute_paired_size_respects_smallest_limit() -> None:
    result = compute_paired_size(
        yes_size=100,
        no_size=80,
        available_cash=20,
        per_market_cap_usd=100,
        remaining_deployable_usd=100,
        estimated_net_cost=0.50,
    )
    assert result == 40
