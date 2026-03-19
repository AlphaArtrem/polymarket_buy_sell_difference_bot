# Polymarket Phase 2.2 Market Quality And Selection Design

Status: Approved for planning
Date: 2026-03-19
Topic: Live opportunity-quality measurement and market classification after VPS deployment

## Summary

This spec defines a narrow phase between transport work and deeper execution accounting.

Phase 2.1 established that the bot can run on an EC2 VPS in `eu-west-1`, consume live public CLOB market data through a persistent WebSocket, and measure realistic request and stream timings. The remaining unanswered question is not "can the bot reach Polymarket fast enough?" It is "which live markets produce enough durable post-cost edge to deserve further research and paper-trading time?"

Phase 2.2 answers that question by adding a live market-quality analysis layer. It will observe streamed order book events, compute per-market opportunity frequency and persistence, and classify markets as `keep`, `watch`, or `drop` using explicit config thresholds.

This phase remains paper-only. It does not introduce richer fill simulation, lot accounting, or authenticated order placement.

## Project Context

Current code can already:

- run on a VPS with stream-first market data
- benchmark Gamma, CLOB REST, and CLOB market WebSocket timings
- record normalized events
- replay recorded events
- run a simple paper-trading engine against live data
- analyze recorded runs for raw and post-cost opportunity counts

Observed VPS results from the current EC2 deployment:

- `gamma` p50 around `8.8 ms`
- `clob_rest` p50 around `28.2 ms`
- `first_message_after_subscribe_ms` p50 around `17.6 ms`
- `market_ws_connect` p50 around `72.8 ms`

Those numbers are good enough to remove region choice and basic transport speed as the main unknown.

What is still missing:

- per-market live activity quality metrics
- opportunity persistence metrics
- a repeatable way to rank markets after a live research run
- config-driven rules for deciding which markets deserve more attention

## Problem Statement

The current system can tell us whether a specific paired book snapshot has raw or post-cost edge, but it does not tell us whether a market is worth monitoring over time.

That leaves three important questions unanswered:

1. Is a market active enough to matter, or is it mostly quiet noise?
2. When post-cost edge appears, does it persist long enough to be interesting?
3. Which markets should survive into later phases for deeper paper-trading and execution-accounting work?

Without a dedicated market-quality layer, the project risks spending time on markets that are too quiet, too brief, or too weak after configured costs.

## Goals

- Measure live market quality from real streamed book events.
- Produce a run-level summary that quickly answers whether a research session was useful.
- Produce a per-market report that acts as the source of truth for later market selection.
- Track both opportunity frequency and opportunity persistence, not just best observed price sums.
- Classify markets as `keep`, `watch`, or `drop` using explicit, config-driven thresholds.
- Reuse the same analysis logic across live streaming runs and recorded replay data.

## Non-Goals

- Honest fill simulation beyond current strict paired execution
- Lot-level portfolio accounting
- Realized or modeled PnL claims
- Authenticated order placement
- Automatic live trading decisions based on the new classification
- Automated discovery of new markets outside the configured universe

## Constraints And Assumptions

- Venue remains Polymarket only.
- Market type remains binary `YES/NO`.
- The phase should build on the existing normalized event stream and paired-book state logic rather than invent a separate data model.
- Quiet markets are valid outcomes and should classify cleanly as `drop`, not fail the run.
- The classification must be explainable from simple thresholds, not opaque heuristics.
- The same thresholds should be reusable later by research and operational tooling.

Important analytical constraint:

- This phase measures opportunity appearance and persistence under live conditions.
- It does not prove that those opportunities are executable or profitable after real queue position, submission delay, or partial fills.
- That work still belongs in later accounting and execution phases.

## Proposed Approach

The recommended approach is a shared market-quality tracker that sits beside the existing paper engine rather than inside it.

Why this approach:

- It keeps Phase 2.2 focused on market selection rather than trade simulation.
- It reuses the same live and replay event boundary already established by the project.
- It avoids overloading the paper engine with selection-specific analytics.
- It creates artifacts that later phases can consume without having to depend on a full execution model.

Alternatives considered and rejected:

1. Extend `run-paper` only
   Convenient, but it mixes market selection concerns into trade-simulation output and makes the phase harder to reason about.

2. Add only a richer replay analyzer
   Useful, but incomplete. The main reason for this phase is to measure live opportunity quality after the VPS and WebSocket work.

3. Pull most of Phase 3 into this phase
   Too broad. It would blur the line between "does live edge appear?" and "can the current simulator account for that edge honestly?"

## System Overview

Phase 2.2 adds a market-quality analysis path with one shared core:

`live stream or replay events -> paired-book observer -> opportunity window tracker -> market classification -> run summary + per-market report`

The tracker should operate on the same normalized order book events already used by replay and live paper mode.

## Core Components

### 1. Research Threshold Settings

Purpose:

- Hold the classification rules in one explicit config section.

Responsibilities:

- Define minimum activity thresholds
- Define minimum post-cost edge thresholds
- Define minimum persistence thresholds
- Separate `keep` rules from softer `watch` rules

Example threshold categories:

- `min_paired_snapshots_per_minute`
- `min_post_cost_opportunities_per_minute`
- `min_total_time_in_edge_ms`
- `min_best_net_edge_bps`
- `min_p50_window_ms`
- `min_max_window_ms`

### 2. Market Quality Tracker

Purpose:

- Aggregate per-market live quality metrics across one run.

Responsibilities:

- Count messages and paired snapshots per market
- Count raw and post-cost opportunity observations
- Track best raw and post-cost sums
- Track active post-cost opportunity windows
- Convert windows into duration statistics and time-in-edge totals
- Record reasons that drive final classification

This tracker should remain stateless with respect to portfolio or execution. It observes markets; it does not trade them.

### 3. Opportunity Window Tracker

Purpose:

- Turn point-in-time post-cost edge checks into persistence metrics.

Responsibilities:

- Start a window when a market first enters post-cost edge
- Extend the window while the market remains in post-cost edge
- Close the window when the edge disappears or the paired book becomes stale/unusable
- Produce:
  - total number of windows
  - total time in edge
  - `p50`, `p95`, and `max` window duration

This component matters because a market that flickers into edge for one instant is different from a market that remains in edge across multiple updates.

### 4. Market Classification Layer

Purpose:

- Convert measurements into an explicit selection decision.

Responsibilities:

- Apply rule-based thresholds to each market
- Assign `keep`, `watch`, or `drop`
- Store machine-readable reasons such as:
  - `too_quiet`
  - `no_post_cost_edge`
  - `edge_too_brief`
  - `edge_too_small`
  - `passes_watch_thresholds`
  - `passes_keep_thresholds`

The classification should be deterministic and auditable from the artifacts alone.

### 5. Live Research CLI

Purpose:

- Run a timed live stream study and write the resulting artifacts.

Responsibilities:

- Subscribe to configured markets through the existing stream path
- Run for a configured duration
- Feed events into the market-quality tracker
- Persist run summary and per-market output
- Reuse the same core tracker for recorded-event analysis

This should be a dedicated research command, not a side effect of `run-paper`.

## Artifact Definitions

Each live research run should emit two primary artifacts.

### Run Summary

Purpose:

- Give a quick answer to "was this run useful and what stood out?"

Suggested fields:

- run metadata:
  - start time
  - end time
  - duration seconds
  - config path
  - threshold block used
- feed metadata:
  - total events
  - total stream messages
  - total paired snapshots
  - total stale paired-book observations
- opportunity metadata:
  - total raw opportunity observations
  - total post-cost opportunity observations
  - total opportunity windows
- classification overview:
  - counts of `keep`, `watch`, and `drop`
  - top markets in each class
- run confidence:
  - `usable`, `low_sample`, or similar status

### Per-Market Quality Report

Purpose:

- Act as the source of truth for later selection decisions.

Each market record should include:

- identity:
  - `market_id`
  - `slug`
  - `question`
- feed quality:
  - message count
  - paired snapshot count
  - stale snapshot count
  - snapshots per minute
- opportunity quality:
  - raw opportunity count
  - post-cost opportunity count
  - raw opportunities per minute
  - post-cost opportunities per minute
  - best raw sum
  - best net sum
  - best net edge bps
- persistence quality:
  - opportunity window count
  - total time in edge ms
  - edge time share of run
  - `p50_window_ms`
  - `p95_window_ms`
  - `max_window_ms`
- classification:
  - `status`
  - `reasons`

JSON should be the primary machine-readable format. A CSV companion is optional if it materially improves quick inspection.

Definition note:

- `best net edge bps` should be defined as the best observed positive distance below `1.00` after configured costs, expressed in basis points.
- Example: `best_net_sum = 0.9975` means `best_net_edge_bps = 25`.

## Classification Model

The classification should stay intentionally simple.

### Keep

A market is `keep` when it satisfies all of the following:

- enough paired snapshots to avoid low-sample noise
- enough post-cost opportunity frequency to matter
- enough observed persistence to avoid one-tick false positives
- enough best observed net edge to justify later research

### Watch

A market is `watch` when it shows some live edge quality but misses one or more of the stricter `keep` thresholds.

Typical examples:

- activity is acceptable but persistence is weak
- one strong edge appears, but frequency is low
- frequency is decent, but the best net edge is still marginal

### Drop

A market is `drop` when:

- it is too quiet
- it never shows post-cost edge
- the observed edge is too brief or too small to be meaningful
- the run sample for that market is too poor to justify continued attention

The classification reasons should be emitted alongside the status so users can see exactly why a market landed in each bucket.

## Data Flow And Reuse

This phase should not create separate live-only math.

The same paired-book analysis logic should support:

- live stream research runs
- recorded-event analysis
- future research sweeps

That keeps market-quality measurements consistent across live observation and offline replay.

When a metric is live-only, such as raw stream-message count, replay mode should either omit it or write an explicit null rather than silently substituting a different meaning.

## Error Handling And Confidence

The system should distinguish between three kinds of "no edge" outcomes:

1. Healthy market, no post-cost edge observed
2. Quiet market with too little activity to say much
3. Stale or unusable paired-book state

Only the third is a feed-quality problem. The first two are valid market outcomes and should be represented explicitly in the artifacts.

Run-level confidence should also be explicit. Very short or sparse runs should complete successfully, but the summary should say they are low-sample and therefore weaker inputs for market selection.

## Testing Strategy

Phase 2.2 should be planned with test coverage for:

- per-market counter aggregation
- opportunity-window open, extend, and close behavior
- duration percentile and time-share calculations
- classification rule evaluation and emitted reasons
- live CLI output on mocked streamed events
- replay analysis using the same tracker logic

The core market-quality tracker should be testable without a live network dependency.

## Acceptance Criteria

Phase 2.2 is successful when:

- a timed live stream study can run on the VPS and complete without using the paper-trading engine
- each run emits a run-level summary and a per-market quality artifact
- the artifact can show which markets are `keep`, `watch`, and `drop`
- each classification includes explicit machine-readable reasons
- the same core analysis can also run against recorded events
- later phases can use the output to narrow the market universe before deeper execution work

## Recommended Next Step

After this spec is approved, the implementation plan should add Phase 2.2 to the roadmap between Phase 2.1 and Phase 3 and then break the work into small TDD-style tasks:

1. threshold config
2. shared market-quality models
3. opportunity-window tracking
4. classification logic
5. live research CLI
6. artifact writers
7. replay reuse and tests
