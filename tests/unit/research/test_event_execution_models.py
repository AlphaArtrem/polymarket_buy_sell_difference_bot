from polymarket_arb.domain.models import DirectionalFillRecord


def test_directional_fill_record_tracks_vwap_and_exit_mode() -> None:
    fill = DirectionalFillRecord(
        market_id="123",
        direction="YES",
        requested_size=10,
        filled_size=8,
        average_price=0.43125,
        status="partial_fill",
        exit_mode="repricing_target",
    )

    assert fill.status == "partial_fill"
    assert fill.exit_mode == "repricing_target"
