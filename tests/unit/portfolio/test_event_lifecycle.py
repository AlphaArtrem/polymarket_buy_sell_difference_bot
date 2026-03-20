from polymarket_arb.portfolio.event_lifecycle import decide_exit_action


def test_decide_exit_action_triggers_repricing_target() -> None:
    action = decide_exit_action(
        exit_mode="repricing_target",
        entry_price=0.42,
        current_price=0.48,
        repricing_target_bps=50,
        elapsed_seconds=30,
        max_holding_seconds=900,
        terminal_signal=False,
        allow_hold_to_resolution=False,
    )

    assert action == "exit_now"


def test_decide_exit_action_holds_terminal_signal_to_resolution() -> None:
    action = decide_exit_action(
        exit_mode="hold_to_resolution",
        entry_price=0.42,
        current_price=0.60,
        repricing_target_bps=50,
        elapsed_seconds=600,
        max_holding_seconds=900,
        terminal_signal=True,
        allow_hold_to_resolution=True,
    )

    assert action == "hold_to_resolution"
