# Polymarket Arbitrage Roadmap

Date: 2026-03-18
Status: Planning set for future sessions

This file is the index for the post-Phase-2 roadmap. It is intentionally short. Each executable phase has its own detailed implementation plan.

## Current Baseline

Completed:

- [Phase 1 plan](/Users/alphaartrem/Desktop/workspace/trading_bot/docs/superpowers/plans/2026-03-17-polymarket-arbitrage-v1.md)
- [Phase 2 plan](/Users/alphaartrem/Desktop/workspace/trading_bot/docs/superpowers/plans/2026-03-17-polymarket-live-data-phase2.md)

Current code can:

- load a curated allowlist
- resolve real Gamma markets by slug
- benchmark VPS latency against Gamma, CLOB REST, the market WebSocket, and optional Polygon RPC
- read live public CLOB books through polling or WebSocket-first streaming
- record normalized events
- replay recorded runs
- run a simple paper-trading engine against live data
- analyze recorded runs for raw and post-cost opportunity counts
- run on a VPS with deployment assets and feed-health artifacts

Current code still does not:

- log detailed opportunity and rejection artifacts
- model inventory lots and lifecycle honestly enough for serious evaluation
- classify markets from live opportunity quality and persistence
- handle long-running live sessions robustly
- support market research sweeps over many runs and parameter sets
- authenticate and place real orders
- provide live-money operational controls

## Remaining Phase Order

1. [Phase 2.1: VPS And Low-Latency Market Data](/Users/alphaartrem/Desktop/workspace/trading_bot/docs/superpowers/plans/2026-03-18-polymarket-phase2-1-vps-websocket-latency.md)
2. [Phase 2.2: Market Quality And Selection](/Users/alphaartrem/Desktop/workspace/trading_bot/docs/superpowers/plans/2026-03-19-polymarket-phase2-2-market-quality-selection.md)
3. [Phase 3: Execution Accounting And Research Artifacts](/Users/alphaartrem/Desktop/workspace/trading_bot/docs/superpowers/plans/2026-03-18-polymarket-phase3-execution-accounting.md)
4. [Phase 4: Streaming Recorder And Live Ops Hardening](/Users/alphaartrem/Desktop/workspace/trading_bot/docs/superpowers/plans/2026-03-18-polymarket-phase4-streaming-recorder-ops.md)
5. [Phase 5: Research Sweeps And Market Selection](/Users/alphaartrem/Desktop/workspace/trading_bot/docs/superpowers/plans/2026-03-18-polymarket-phase5-research-sweeps.md)
6. [Phase 6: Authenticated Execution And Safety Rails](/Users/alphaartrem/Desktop/workspace/trading_bot/docs/superpowers/plans/2026-03-18-polymarket-phase6-authenticated-execution.md)
7. [Phase 7: Live Rollout And Runtime Operations](/Users/alphaartrem/Desktop/workspace/trading_bot/docs/superpowers/plans/2026-03-18-polymarket-phase7-live-rollout-ops.md)

## Dependency Notes

- Phase 2.1 should happen before any serious live evaluation, because the current live adapter is polling-only and cannot tell us whether missed opportunities are strategy failures or latency failures.
- Phase 2.2 should happen before deeper Phase 3 accounting work, because it narrows the live market universe using real streamed evidence instead of intuition.
- Phase 3 should happen after Phase 2.2, because the honest execution and lot-accounting work is most valuable once the market universe has already been filtered by live quality.
- Phase 4 builds on Phase 2.1 by hardening reconnect, metadata, and long-running stream behavior after the first-cut VPS streaming path exists.
- Phase 5 depends on Phase 3 artifacts and benefits from Phase 2.1, Phase 2.2, and Phase 4 capture quality.
- Phase 6 should start only after Phase 3 and Phase 5 show a repeatable edge worth trading.
- Phase 7 should start only after Phase 6 is implemented and manually tested with tiny size.

## Suggested Session Pattern

Use one chat per phase:

- load this roadmap file
- load the relevant phase plan file
- execute only that phase
- stop and verify before moving to the next plan
