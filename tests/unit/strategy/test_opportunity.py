from polymarket_arb.strategy.opportunity import evaluate_opportunity


def test_evaluate_opportunity_rejects_edge_consumed_by_costs() -> None:
    result = evaluate_opportunity(
        yes_ask=0.43,
        no_ask=0.54,
        raw_alert_threshold=0.99,
        fee_rate=0.01,
        slippage_buffer=0.02,
        operational_buffer=0.005,
    )

    assert result.accepted is False
    assert result.rejection_reason == "threshold_not_met_after_costs"
