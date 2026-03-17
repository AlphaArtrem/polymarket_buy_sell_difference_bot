from dataclasses import dataclass
from typing import Iterable, Optional

from polymarket_arb.domain.models import BookLevel


@dataclass
class FillResult:
    status: str
    filled_size: float
    total_cost: float


def _consume_cost(levels: Iterable[BookLevel], size: float) -> Optional[float]:
    remaining = size
    total = 0.0
    for level in levels:
        take = min(level.size, remaining)
        total += take * level.price
        remaining -= take
        if remaining == 0:
            return total
    return None


def simulate_strict_pair_fill(
    *, yes_asks: list[BookLevel], no_asks: list[BookLevel], target_size: float
) -> FillResult:
    yes_available = sum(level.size for level in yes_asks)
    no_available = sum(level.size for level in no_asks)
    if min(yes_available, no_available) < target_size:
        return FillResult("broken_pair", 0.0, 0.0)

    yes_cost = _consume_cost(yes_asks, target_size)
    no_cost = _consume_cost(no_asks, target_size)
    return FillResult("filled", target_size, float(yes_cost or 0.0) + float(no_cost or 0.0))
