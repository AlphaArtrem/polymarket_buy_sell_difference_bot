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
- read live public CLOB books through polling
- record normalized events
- replay recorded runs
- run a simple paper-trading engine against live data

Current code still does not:

- log detailed opportunity and rejection artifacts
- model inventory lots and lifecycle honestly enough for serious evaluation
- handle long-running live sessions robustly
- support market research sweeps over many runs and parameter sets
- authenticate and place real orders
- provide live-money operational controls

## Remaining Phase Order

1. [Phase 3: Execution Accounting And Research Artifacts](/Users/alphaartrem/Desktop/workspace/trading_bot/docs/superpowers/plans/2026-03-18-polymarket-phase3-execution-accounting.md)
2. [Phase 4: Streaming Recorder And Live Ops Hardening](/Users/alphaartrem/Desktop/workspace/trading_bot/docs/superpowers/plans/2026-03-18-polymarket-phase4-streaming-recorder-ops.md)
3. [Phase 5: Research Sweeps And Market Selection](/Users/alphaartrem/Desktop/workspace/trading_bot/docs/superpowers/plans/2026-03-18-polymarket-phase5-research-sweeps.md)
4. [Phase 6: Authenticated Execution And Safety Rails](/Users/alphaartrem/Desktop/workspace/trading_bot/docs/superpowers/plans/2026-03-18-polymarket-phase6-authenticated-execution.md)
5. [Phase 7: Live Rollout And Runtime Operations](/Users/alphaartrem/Desktop/workspace/trading_bot/docs/superpowers/plans/2026-03-18-polymarket-phase7-live-rollout-ops.md)

## Dependency Notes

- Phase 3 should happen before any serious replay research, because the current summary is too thin to trust.
- Phase 4 should happen before long live sessions, because the current live adapter is polling-only and not resilient enough for operational use.
- Phase 5 depends on Phase 3 artifacts and benefits from Phase 4 capture quality.
- Phase 6 should start only after Phase 3 and Phase 5 show a repeatable edge worth trading.
- Phase 7 should start only after Phase 6 is implemented and manually tested with tiny size.

## Suggested Session Pattern

Use one chat per phase:

- load this roadmap file
- load the relevant phase plan file
- execute only that phase
- stop and verify before moving to the next plan
