from polymarket_arb.structure.models import StructureOpportunity


class StructureScanner:
    def __init__(
        self,
        *,
        min_raw_gap_bps: float,
        min_net_gap_bps: float,
        fee_rate: float,
        slippage_buffer: float,
        operational_buffer: float,
        min_executable_size: float = 0.0,
    ) -> None:
        self.min_raw_gap_bps = min_raw_gap_bps
        self.min_net_gap_bps = min_net_gap_bps
        self.fee_rate = fee_rate
        self.slippage_buffer = slippage_buffer
        self.operational_buffer = operational_buffer
        self.min_executable_size = min_executable_size

    def scan_mutually_exclusive_yes(
        self,
        *,
        key: str,
        yes_quotes: list[dict[str, float]],
    ) -> StructureOpportunity | None:
        total_price = sum(float(quote.get("price", 0.0)) for quote in yes_quotes)
        executable_size = min(
            (float(quote.get("size", 0.0)) for quote in yes_quotes),
            default=0.0,
        )
        return self._build_opportunity(
            key=key,
            relationship_type="mutually_exclusive_yes",
            total_price=total_price,
            executable_size=executable_size,
        )

    def scan_implication_pair(
        self,
        *,
        key: str,
        yes_child_price: float,
        no_parent_price: float,
        child_size: float,
        parent_size: float,
    ) -> StructureOpportunity | None:
        return self._build_opportunity(
            key=key,
            relationship_type="implies_yes",
            total_price=yes_child_price + no_parent_price,
            executable_size=min(child_size, parent_size),
        )

    def _build_opportunity(
        self,
        *,
        key: str,
        relationship_type: str,
        total_price: float,
        executable_size: float,
    ) -> StructureOpportunity | None:
        raw_gap_bps = round(max(0.0, 1.0 - total_price) * 10_000, 4)
        total_cost = (
            total_price
            + self.fee_rate
            + self.slippage_buffer
            + self.operational_buffer
        )
        net_gap_bps = round(max(0.0, 1.0 - total_cost) * 10_000, 4)
        if raw_gap_bps < self.min_raw_gap_bps:
            return None
        if net_gap_bps < self.min_net_gap_bps:
            return None
        if executable_size < self.min_executable_size:
            return None
        return StructureOpportunity(
            key=key,
            relationship_type=relationship_type,
            raw_gap_bps=raw_gap_bps,
            net_gap_bps=net_gap_bps,
            executable_size=executable_size,
        )
