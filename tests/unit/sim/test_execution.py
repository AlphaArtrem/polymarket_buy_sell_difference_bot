from polymarket_arb.domain.models import BookLevel
from polymarket_arb.sim.execution import simulate_strict_pair_fill


def test_simulate_strict_pair_fill_succeeds_when_both_books_have_depth() -> None:
    result = simulate_strict_pair_fill(
        yes_asks=[BookLevel(price=0.43, size=10)],
        no_asks=[BookLevel(price=0.54, size=10)],
        target_size=5,
    )

    assert result.status == "filled"
    assert result.filled_size == 5
