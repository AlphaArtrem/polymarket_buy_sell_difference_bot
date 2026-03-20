from polymarket_arb.research.event_ranking import rank_event_markets


def test_rank_event_markets_prefers_repeatable_edge_over_single_spike() -> None:
    ranked = rank_event_markets(
        [
            {
                "slug": "steady",
                "accepted_signal_count": 4,
                "median_edge_bps": 35,
                "source_health": 1.0,
            },
            {
                "slug": "spiky",
                "accepted_signal_count": 1,
                "median_edge_bps": 80,
                "source_health": 0.4,
            },
        ]
    )

    assert ranked[0].slug == "steady"
