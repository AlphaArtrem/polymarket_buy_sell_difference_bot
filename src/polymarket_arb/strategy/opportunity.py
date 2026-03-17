from dataclasses import dataclass
from typing import Optional


@dataclass
class OpportunityDecision:
    accepted: bool
    estimated_net_cost: float
    rejection_reason: Optional[str]


def evaluate_opportunity(
    *,
    yes_ask: float,
    no_ask: float,
    raw_alert_threshold: float,
    fee_rate: float,
    slippage_buffer: float,
    operational_buffer: float,
) -> OpportunityDecision:
    gross = yes_ask + no_ask
    if gross >= raw_alert_threshold:
        return OpportunityDecision(False, gross, "raw_threshold_not_met")

    estimated_net_cost = gross + fee_rate + slippage_buffer + operational_buffer
    if estimated_net_cost >= 1.0:
        return OpportunityDecision(
            False, estimated_net_cost, "threshold_not_met_after_costs"
        )

    return OpportunityDecision(True, estimated_net_cost, None)
