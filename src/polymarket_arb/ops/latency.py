from __future__ import annotations

import json
import time
from statistics import median
from typing import Any

import httpx
import websockets


def summarize_samples(samples_ms: list[float]) -> dict[str, float]:
    ordered = sorted(samples_ms)
    if not ordered:
        return {"count": 0, "min_ms": 0.0, "p50_ms": 0.0, "max_ms": 0.0}
    return {
        "count": float(len(ordered)),
        "min_ms": ordered[0],
        "p50_ms": float(median(ordered)),
        "max_ms": ordered[-1],
    }


def measure_http_endpoint(
    base_url: str,
    *,
    method: str = "GET",
    path: str = "/",
    params: dict[str, Any] | None = None,
    json_body: dict[str, Any] | list[Any] | None = None,
    samples: int = 5,
    timeout: float = 5.0,
) -> list[float]:
    latencies: list[float] = []
    with httpx.Client(base_url=base_url, timeout=timeout) as client:
        for _ in range(max(samples, 0)):
            started = time.perf_counter()
            response = client.request(
                method,
                path,
                params=params,
                json=json_body,
            )
            response.raise_for_status()
            latencies.append(round((time.perf_counter() - started) * 1000, 3))
    return latencies


def measure_websocket_connect(
    url: str,
    *,
    subscription_payload: dict[str, Any] | None = None,
    samples: int = 5,
) -> list[float]:
    latencies: list[float] = []
    for _ in range(max(samples, 0)):
        started = time.perf_counter()
        async def _probe() -> None:
            async with websockets.connect(url) as websocket:
                if subscription_payload is not None:
                    await websocket.send(json.dumps(subscription_payload))
        import asyncio

        asyncio.run(_probe())
        latencies.append(round((time.perf_counter() - started) * 1000, 3))
    return latencies


def measure_websocket_subscription(
    url: str,
    *,
    subscription_payload: dict[str, Any],
    samples: int = 3,
    messages_per_sample: int = 3,
    timeout: float = 10.0,
) -> dict[str, list[float]]:
    first_message_latencies: list[float] = []
    steady_state_gaps: list[float] = []

    for _ in range(max(samples, 0)):
        async def _probe() -> tuple[float | None, list[float]]:
            async with websockets.connect(url) as websocket:
                started = time.perf_counter()
                await websocket.send(json.dumps(subscription_payload))
                first_raw = await asyncio.wait_for(websocket.recv(), timeout=timeout)
                _ = first_raw
                first_latency = round((time.perf_counter() - started) * 1000, 3)

                gaps: list[float] = []
                last = time.perf_counter()
                for _ in range(max(messages_per_sample - 1, 0)):
                    await asyncio.wait_for(websocket.recv(), timeout=timeout)
                    now = time.perf_counter()
                    gaps.append(round((now - last) * 1000, 3))
                    last = now
                return first_latency, gaps

        import asyncio

        first_latency, gaps = asyncio.run(_probe())
        if first_latency is not None:
            first_message_latencies.append(first_latency)
        steady_state_gaps.extend(gaps)

    return {
        "first_message_after_subscribe_ms": first_message_latencies,
        "steady_state_message_gap_ms": steady_state_gaps,
    }
