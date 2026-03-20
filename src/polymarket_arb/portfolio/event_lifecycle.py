def decide_exit_action(
    *,
    exit_mode: str,
    entry_price: float,
    current_price: float,
    repricing_target_bps: float,
    elapsed_seconds: int,
    max_holding_seconds: int,
    terminal_signal: bool,
    allow_hold_to_resolution: bool,
) -> str:
    if exit_mode == "hold_to_resolution" and terminal_signal and allow_hold_to_resolution:
        return "hold_to_resolution"
    if exit_mode == "repricing_target":
        target_price = entry_price + (repricing_target_bps / 10_000)
        if current_price >= target_price:
            return "exit_now"
    if elapsed_seconds >= max_holding_seconds:
        return "exit_now"
    return "hold"
