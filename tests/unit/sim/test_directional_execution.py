from polymarket_arb.domain.models import BookLevel
from polymarket_arb.sim.directional import simulate_directional_fill


def test_simulate_directional_fill_returns_vwap_for_multi_level_buy() -> None:
    fill = simulate_directional_fill(
        side="buy",
        book_levels=[
            BookLevel(price=0.43, size=5),
            BookLevel(price=0.44, size=5),
        ],
        requested_size=8,
        slippage_buffer=0.0,
    )

    assert fill.status == "filled"
    assert fill.filled_size == 8
    assert round(fill.average_price, 4) == 0.4338


def test_simulate_directional_fill_marks_partial_fill_when_depth_runs_out() -> None:
    fill = simulate_directional_fill(
        side="sell",
        book_levels=[BookLevel(price=0.58, size=3)],
        requested_size=5,
        slippage_buffer=0.0,
    )

    assert fill.status == "partial_fill"
    assert fill.filled_size == 3
