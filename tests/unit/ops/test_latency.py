from polymarket_arb.ops.latency import summarize_samples


def test_summarize_samples_returns_basic_percentiles() -> None:
    summary = summarize_samples([8.0, 10.0, 12.0, 20.0, 30.0])

    assert summary["count"] == 5
    assert summary["min_ms"] == 8.0
    assert summary["p50_ms"] == 12.0
    assert summary["max_ms"] == 30.0


def test_summarize_samples_handles_empty_input() -> None:
    summary = summarize_samples([])

    assert summary["count"] == 0
    assert summary["p50_ms"] == 0.0
