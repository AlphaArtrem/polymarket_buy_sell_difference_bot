# Polymarket Full-Set Arbitrage Bot Design

Status: Approved for planning
Date: 2026-03-17
Topic: Beginner-first Polymarket arbitrage bot with shared backtesting and live paper-trading core

## Summary

This spec defines the first slice of a Polymarket bot that targets binary full-set arbitrage on a curated set of markets.

The bot will:

- Watch curated binary Polymarket markets in real time.
- Detect cases where buying both `YES` and `NO` can produce positive expected value after modeled costs.
- Simulate taker-only execution on both legs.
- Reuse the same trading core in both historical replay and live paper-trading modes.
- Enforce portfolio constraints from day one.

The bot will not place real orders in this phase.

## Project Context

The workspace for this project is currently greenfield. There is no existing application structure, no prior implementation, and no prior local design documentation in `/Users/alphaartrem/Desktop/workspace/trading_bot`.

The user wants to learn in stages:

1. Backtesting
2. Paper trading
3. Small live deployment with gradually increasing capital

This first spec covers only the Polymarket portion of that path.

## Problem Statement

Each binary Polymarket market resolves to exactly one unit of collateral across a complete `YES + NO` pair. In ideal pricing, the taker cost of buying both sides should not exceed `1.00`. In practice, fast-moving markets and thin orderbooks can create temporary dislocations where both sides can be bought for less than `1.00`.

The naive version of this idea is: if `YES ask + NO ask < 1.00`, buy both and lock in profit.

The realistic version is more constrained:

- Fees may apply.
- Visible size may be too small.
- One leg may fill while the other does not.
- Historical price series alone are not enough to reconstruct true taker execution.
- Profit is not realized until the full paired position is actually closed via merge or held to resolution.

This spec is designed around the realistic version, not the naive one.

## Goals

- Build a single event-driven core that supports both replay and live paper trading.
- Focus only on curated binary Polymarket markets in the first version.
- Use taker-only execution for both legs in the first version.
- Detect, size, simulate, and track full-set arbitrage opportunities.
- Model position lifecycle honestly enough that "risk-free" claims are only made for completed pairs with a valid realization path.
- Produce artifacts that help answer whether the strategy is actually executable, not just theoretically attractive.

## Non-Goals

- Real-money execution
- Maker orders
- Cross-market or cross-event arbitrage
- Negative-risk multi-outcome market strategies
- Wallet-following or social-signal strategies
- Hyperliquid integration in this spec
- Fully automated market selection across the entire exchange

## Constraints And Assumptions

- Venue: Polymarket only
- Market type: binary `YES/NO` markets only
- Initial market universe: curated allowlist of roughly 10-20 markets
- Execution style: taker-only on both legs
- Modes: replay backtesting and live paper trading from one shared core
- Portfolio controls: included from day one
- Paper trading is local simulation against live public market data, not real exchange execution

Important planning constraint:

- Polymarket documents public market discovery, current orderbooks, WebSocket streaming, fee flags, and historical price series.
- The referenced public docs do not describe a historical full-depth orderbook replay endpoint.
- Because of that, realistic execution backtesting must rely on captured orderbook snapshots and market events recorded by our own collector.
- Historical price series can still be used for coarse research, sanity checks, and gap-filling, but not as the sole source for depth-aware taker-fill simulation.

This means the first implementation plan should treat market-data recording as a first-class part of the system, not a side utility.

## Official References

These sources ground the design in current Polymarket docs:

- [Market Data Overview](https://docs.polymarket.com/market-data/overview)
- [Orderbook](https://docs.polymarket.com/trading/orderbook)
- [WebSocket Overview](https://docs.polymarket.com/market-data/websocket/overview)
- [Get prices history](https://docs.polymarket.com/api-reference/markets/get-prices-history)
- [Merge Tokens](https://docs.polymarket.com/trading/ctf/merge)
- [Fees](https://docs.polymarket.com/trading/fees)

## Proposed Approach

The recommended architecture is a unified event-driven core with separate input adapters for replay and live data.

Why this approach:

- It matches the desired learning path of backtesting first, then paper trading.
- It keeps trade logic consistent between modes.
- It reduces drift between "research code" and "live simulation code."
- It forces execution assumptions to be explicit and testable.

Alternatives considered and rejected:

1. Separate backtest and live scripts with shared helpers
   Faster to start, but likely to diverge quickly in fills, fees, and risk rules.

2. Batch snapshot analyzer only
   Useful for research, but too weak for realistic paper trading and portfolio lifecycle tracking.

## System Overview

The first version consists of the following major parts:

1. Market catalog loader
2. Market data recorder
3. Replay adapter
4. Live adapter
5. Normalized market state store
6. Opportunity engine
7. Position-sizing engine
8. Execution simulator
9. Inventory lifecycle engine
10. Portfolio and risk manager
11. Reporting and artifact writers

High-level flow:

`Gamma market metadata + CLOB orderbooks/WebSocket + recorded snapshots -> normalized events -> opportunity engine -> execution simulator -> portfolio ledger -> run artifacts`

## Core Components

### 1. Market Catalog Loader

Purpose:

- Load the user-maintained allowlist of markets to watch.
- Resolve the paired `YES` and `NO` token IDs for each binary market.
- Persist market metadata needed for filtering and reporting.

Responsibilities:

- Pull market metadata from Polymarket discovery endpoints.
- Validate that each configured market is binary and orderbook-enabled.
- Track fields such as:
  - event slug
  - market question
  - condition ID
  - `YES` token ID
  - `NO` token ID
  - market status
  - `feesEnabled` or equivalent fee metadata

Out of scope:

- Automated discovery and ranking of all active markets

### 2. Market Data Recorder

Purpose:

- Record the raw data needed to replay realistic market conditions later.

Responsibilities:

- Subscribe to live market data for the curated allowlist.
- Persist normalized orderbook snapshots and price updates with timestamps.
- For v1, record the ask-side ladder needed for taker simulation on both `YES` and `NO`, rather than trying to capture every possible market microstructure detail.
- Write replayable artifacts in a format suitable for deterministic historical simulation.

Minimum replay requirement:

- The recorder must preserve enough information to reconstruct the visible paired ask depth seen by the strategy at decision time.
- The implementation plan should prefer normalized update events plus periodic snapshots over a loose collection of ad hoc CSV exports.

This component matters because replay quality depends on recorded depth and timing, not just end-of-minute price history.

### 3. Replay Adapter

Purpose:

- Feed recorded historical events into the shared trading core.

Responsibilities:

- Read captured snapshot files in timestamp order.
- Reconstruct market-state updates deterministically.
- Expose replay controls such as start time, end time, speed, and selected markets.

### 4. Live Adapter

Purpose:

- Feed current public market data into the same trading core used by replay.

Responsibilities:

- Connect to relevant market-data endpoints and streams.
- Translate external payloads into internal normalized events.
- Maintain connection health, reconnection behavior, and data freshness signaling.

### 5. Normalized Market State Store

Purpose:

- Maintain the latest usable state for each `YES` and `NO` book.

Responsibilities:

- Store best ask, visible ask depth, timestamp, tick size, and freshness state.
- Keep paired `YES` and `NO` state aligned under one logical market view.
- Mark markets unusable if data is stale, incomplete, or inconsistent.

### 6. Opportunity Engine

Purpose:

- Decide when an observed market state is worth attempting.

Core calculation:

`yes_ask + no_ask + estimated_fees + estimated_slippage + operational_buffer < 1.00`

Rules:

- A raw alert may be emitted when top-of-book price sum drops below a configurable threshold such as `0.99`.
- Actual executable opportunities must be evaluated net of costs and based on available size on both sides.
- Markets with ambiguous fee configuration, stale data, or insufficient paired depth are rejected.

The engine should emit both:

- accepted opportunities
- rejected opportunities with explicit reasons

Rejected-opportunity logging is important for learning why social-media "free money" examples are often not executable.

### 7. Position-Sizing Engine

Purpose:

- Convert an opportunity into a safe paired order size.

Inputs:

- visible paired ask depth
- available cash
- per-market cap
- total capital cap
- open inventory count
- minimum order size

Responsibilities:

- Compute the largest paired size that stays within all risk limits.
- Refuse trades that only clear thresholds at uneconomically small size.
- Avoid capital concentration in a single market.

### 8. Execution Simulator

Purpose:

- Model taker-only execution on both sides of the binary pair.

Behavior:

- Consume ask liquidity from the top of book outward.
- Apply size-aware fill pricing rather than assuming infinite liquidity at the best ask.
- Model one of two outcomes:
  - full paired execution
  - partial or broken execution

Default operating mode:

- `strict paired mode`
- A trade is counted as successful only if both legs can be fully simulated within the same accepted market state snapshot.

Secondary diagnostic mode:

- `degraded mode`
- Partial fills are allowed for research, but they are classified separately as execution failures or broken-pair inventory.

The first implementation plan should default to strict paired mode and keep degraded mode available for later diagnostics.

### 9. Inventory Lifecycle Engine

Purpose:

- Track how a completed pair becomes realized PnL.

Responsibilities:

- Create inventory lots for every completed `YES + NO` pair.
- Track entry timestamp, average cost, expected payout, expected fees, and lifecycle state.
- Support the two conceptual realization paths:
  - merge back to collateral
  - hold through resolution

Default v1 accounting rule:

- The first implementation should treat completed pairs as realized only at modeled market resolution, paying out `1.00` per completed pair.
- Merge should be represented as a documented extension point or secondary accounting mode, not as required v1 functionality.

The first version does not need real onchain merge execution, but it must model the accounting path honestly enough that realized PnL is not booked immediately at entry.

### 10. Portfolio And Risk Manager

Purpose:

- Enforce hard constraints at run time.

Required controls:

- max capital per market
- max total deployed capital
- max concurrent paired lots
- max broken-pair exposure
- cooldown after execution in the same market
- stale-data rejection

Responsibilities:

- Maintain free cash, locked cash, open lots, broken-pair exposure, and cumulative fees.
- Prevent the simulator from entering trades that look good individually but overextend the account.

### 11. Reporting And Artifact Writers

Purpose:

- Produce outputs that are useful for learning, debugging, and later planning.

Required outputs:

- backtest summary
- live paper-trading session summary
- detailed trade log
- rejected-opportunity log
- inventory ledger
- portfolio time series
- machine-readable JSON or CSV artifacts for analysis

## Data Model

The implementation plan should define stable, small contracts for the following records:

### Market Catalog Entry

- logical market identifier
- event slug or event identifier
- question text
- condition ID
- `YES` token ID
- `NO` token ID
- fee metadata
- status metadata

### Market State

- market identifier
- side (`YES` or `NO`)
- best ask
- ask depth ladder
- timestamp
- tick size
- minimum order size
- freshness flag

### Opportunity Record

- market identifier
- observed `YES` ask
- observed `NO` ask
- gross combined cost
- estimated fees
- estimated slippage
- operational buffer
- net estimated cost
- executable paired size
- decision outcome
- rejection reason if applicable

### Paper Trade Record

- run ID
- market identifier
- attempt timestamp
- requested paired size
- filled `YES` size and price
- filled `NO` size and price
- fee estimate
- success or failure classification

### Inventory Lot

- lot ID
- market identifier
- paired size
- total cost basis
- expected payout
- lifecycle state
- realized PnL when complete

### Portfolio State

- run ID
- timestamp
- free cash
- locked cash
- cumulative fees
- open paired lots
- broken-pair exposure
- realized PnL
- unrealized PnL

## Modes

### Replay Backtesting Mode

Purpose:

- Evaluate how the strategy would have behaved on recorded data.

Inputs:

- recorded market events
- market allowlist
- strategy thresholds
- risk parameters

Outputs:

- run summary
- event-by-event decisions
- trade and inventory logs

### Live Paper-Trading Mode

Purpose:

- Run the same decision logic on current public data without sending real orders.

Inputs:

- live public market data streams
- market allowlist
- strategy thresholds
- risk parameters

Outputs:

- live decision stream
- simulated trade attempts
- session summary
- operational logs

The live mode is not a substitute for real execution, but it is the correct intermediate step before using real capital.

## Opportunity Detection And Entry Rules

The first version should make a hard distinction between:

- a market mispricing signal
- an actually executable arbitrage

Signal threshold:

- configured alert when `YES ask + NO ask` drops below a raw threshold

Execution threshold:

- only execute when the estimated net cost remains below `1.00` after fees, slippage, and operational buffer

Additional entry conditions:

- market is in curated allowlist
- both sides are fresh
- both sides have enough visible ask size
- position size is above minimum order size
- portfolio caps are not breached

## Error Handling And Failure Classification

The bot should classify failures rather than collapsing them into generic "missed trade" outcomes.

Required classifications:

- stale market data
- missing paired book
- insufficient depth
- threshold not met after fees
- threshold not met after slippage
- per-market cap exceeded
- total capital cap exceeded
- broken-pair execution
- invalid market metadata
- feed disconnect or replay corruption

This classification layer is important because it will show whether the idea fails because the strategy is bad or because the market-data and execution assumptions are weak.

## Testing Strategy

The implementation plan should include tests for:

### Unit Tests

- opportunity-cost calculations
- fee handling
- slippage estimation
- position sizing
- portfolio cap enforcement

### Deterministic Replay Tests

- identical recorded inputs produce identical outputs
- market transitions from valid to invalid opportunity are handled predictably
- stale-data flags prevent entry

### Failure-Mode Tests

- one leg available, other leg unavailable
- one leg fully fills, the other partially fills
- market fee metadata changes behavior
- tiny visible edge disappears after costs

### Acceptance Scenarios

- a simple recorded market produces at least one accepted trade
- a simple recorded market produces only rejected trades with correct reasons
- live paper mode emits the same opportunity decision as replay when fed the same normalized events

## Success Criteria For This Spec

The first implementation should be considered successful if it can:

- replay recorded Polymarket market data for a curated allowlist
- run the same arbitrage logic in replay and live paper modes
- produce deterministic opportunity and trade decisions
- simulate paired taker entries with explicit cost modeling
- track inventory and portfolio constraints honestly
- emit artifacts that are strong enough to support a later go or no-go decision for small live deployment

## Risks And Planning Notes

These are not blockers, but they must shape the implementation plan:

1. Historical realism depends on recorded depth, not just prices.
2. Paper trading can only simulate live execution quality, not prove it.
3. Public orderbooks may change between observed updates, so even strict paired simulation remains an approximation.
4. Fee treatment must be explicit because some markets have fees enabled.
5. A greenfield workspace means the plan should include project scaffolding, configuration, and artifact layout from scratch.

## Future Phases

This section captures the intended expansion path so v1 is built with clean upgrade points.

### Phase 0: Data Capture Foundation

- Add a durable recorder for curated market snapshots and market events.
- Build a small labeled replay corpus.
- Validate replay fidelity before trusting backtest results.

### Phase 1: Shared Replay And Live Paper Core

- Implement the v1 architecture in this spec.
- Support curated binary markets only.
- Keep execution taker-only and simulated.

### Phase 2: Execution Realism And Research Tooling

- Add richer diagnostics for partial fills and broken pairs.
- Improve reporting, dashboards, and parameter sweeps.
- Add better market-selection heuristics for the curated universe.

### Phase 3: Small Live Trading With Hard Safety Rails

- Add authenticated order placement.
- Start with tiny capital and strong kill switches.
- Require manual review of paper-trading results before enabling live mode.
- Keep strict per-market and total-capital limits.

### Phase 4: Broader Strategy Expansion

- Expand to larger market universes once the binary full-set bot is reliable.
- Add more nuanced execution tactics.
- Explore whether the architecture should generalize to other venues, including Hyperliquid, without compromising clarity in the Polymarket path.

## Out Of Scope For Planning Handoff

This spec is ready to hand off to an implementation-planning step focused on the first phase of actual build work. The next planning document should break the v1 architecture into sequenced implementation tasks, but it should not yet plan real-money execution.
