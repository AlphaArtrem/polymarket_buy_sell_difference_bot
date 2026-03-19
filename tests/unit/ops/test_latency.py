from polymarket_arb.ops import latency
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


def test_measure_websocket_subscription_keeps_first_message_on_gap_timeout(
    monkeypatch,
) -> None:
    class StubWebSocket:
        async def send(self, payload):
            return None

        async def recv(self):
            if not hasattr(self, "_called"):
                self._called = True
                return '[{"asset_id":"a1","asks":[],"timestamp":"1"}]'
            raise TimeoutError("no more messages")

    class StubConnection:
        async def __aenter__(self):
            return StubWebSocket()

        async def __aexit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(latency.websockets, "connect", lambda url: StubConnection())

    result = latency.measure_websocket_subscription(
        "wss://example.test/ws",
        subscription_payload={"assets_ids": ["a1"], "type": "market"},
        samples=1,
        messages_per_sample=3,
        timeout=0.001,
    )

    assert len(result["first_message_after_subscribe_ms"]) == 1
    assert result["steady_state_message_gap_ms"] == []
