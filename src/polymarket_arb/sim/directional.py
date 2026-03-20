from polymarket_arb.domain.models import BookLevel, DirectionalFillRecord


def simulate_directional_fill(
    *,
    side: str,
    book_levels: list[BookLevel],
    requested_size: float,
    slippage_buffer: float,
    market_id: str = "",
    direction: str = "",
    exit_mode: str = "",
) -> DirectionalFillRecord:
    del side

    remaining_size = requested_size
    filled_size = 0.0
    total_cost = 0.0

    for level in book_levels:
        if remaining_size <= 0:
            break
        take_size = min(level.size, remaining_size)
        fill_price = level.price + slippage_buffer
        total_cost += take_size * fill_price
        filled_size += take_size
        remaining_size -= take_size

    if filled_size == 0:
        status = "no_fill"
        average_price = 0.0
    elif filled_size < requested_size:
        status = "partial_fill"
        average_price = round(total_cost / filled_size, 8)
    else:
        status = "filled"
        average_price = round(total_cost / filled_size, 8)

    return DirectionalFillRecord(
        market_id=market_id,
        direction=direction,
        requested_size=requested_size,
        filled_size=filled_size,
        average_price=average_price,
        status=status,
        exit_mode=exit_mode,
    )
