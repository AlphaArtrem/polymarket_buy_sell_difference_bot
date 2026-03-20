# Polymarket Edge Research And Trading Platform Design

Status: Approved for planning
Date: 2026-03-20
Topic: Pivot from full-set arbitrage to evidence-driven Polymarket trading, with objective external-signal research as the next phase

## Summary

This spec replaces the original single-strategy full-set arbitrage framing with a broader design based on what the project has now learned from live market study work.

The important result is no longer in doubt:

- the current infrastructure is good enough to stream, record, replay, and study live Polymarket books
- the recent three-bucket market study did not find raw top-of-book full-set arbitrage in the tested market set
- the blocker is now strategy edge, not basic transport latency

The project should therefore pivot from "build a bot around one assumed arbitrage edge" to "build a disciplined platform for discovering, testing, and eventually trading only edges that survive real evidence."

The recommended next phase is:

- objective-source event research for one-sided informational trading

That phase will:

- expand the candidate market universe
- attach markets to explicit, auditable external sources
- ingest source updates and compare them to Polymarket price response
- measure lead-lag windows, depth, and executable paper edge
- rank markets and source types by observed edge quality

This phase remains paper-only and research-first. No authenticated trading belongs in the immediate next phase.

## Project Context

The repo is no longer greenfield. Current code can already:

- load and refresh a configured Polymarket market catalog
- resolve token IDs and market metadata from Gamma
- benchmark HTTP and WebSocket latency
- stream public CLOB market data
- record normalized live events
- replay recorded runs deterministically
- run paper trading over the same shared engine shape
- analyze market quality for a configured market set

Recent research changed the strategic conclusion:

- small, medium, and large market buckets all produced `raw_opportunity_count=0`
- the best observed raw sums stayed at or above parity rather than below it
- more message traffic did not create raw edge
- one study run died on a WebSocket disconnect, confirming that operational hardening still matters, but not as the main source of lost edge

The important implication is:

- the current market set is not a good fit for top-of-book full-set arbitrage
- lowering thresholds will not create profit when raw edge is absent
- deeper accounting work is still valuable later, but not as the next strategic move

This spec makes the main design document the durable source of truth for the new direction.

## Problem Statement

The project no longer needs to answer "can a curated set of binary markets produce taker full-set arbitrage?"

The live study already answered that for the current universe:

- not in a way worth pursuing

The new problem is:

- which Polymarket strategy classes can plausibly produce real edge under current venue mechanics
- how can the bot measure that edge with enough discipline to reject false positives quickly
- how can the existing streaming, recording, replay, and research stack be reused instead of discarded

The next strategy should satisfy at least one of these edge sources:

1. objective external information reaches us before the market fully reprices
2. multiple related markets become logically inconsistent
3. passive liquidity incentives compensate for adverse selection and inventory risk

The recommended immediate focus is the first category because it offers the best combination of upside, testability, and fit with the current codebase.

## Strategic Direction

### Primary Recommendation

Pursue objective-source event trading first.

Meaning:

- trade only markets whose resolution criteria map to an explicit, auditable source
- detect source updates outside Polymarket
- measure whether the market lags that source enough to permit a one-sided entry after costs
- paper trade that edge before any authenticated execution work

Why this is the best next move:

- it targets a real edge source rather than a threshold artifact
- it reuses the current streaming and replay infrastructure
- it creates measurable research outputs even if the final answer is negative
- it does not depend on winning a pure speed race across every market

### Secondary Future Directions

These remain worthwhile, but they should not be the next phase:

1. Cross-market and negative-risk structure research
   Good strategic fit with the current arbitrage mindset, but it depends on a broader market graph and more relationship logic than the current system has.

2. Passive maker and incentive capture
   More attractive than before because Polymarket now has liquidity rewards and daily maker rebates in eligible markets, but this path needs authenticated trading, quote management, and inventory controls that are too large for the immediate pivot.

### Directions To Avoid Right Now

- more threshold tuning on the current full-set arb path
- broad, generic NLP news trading without explicit source discipline
- sports taker automation as the first event domain

## Goals

- Reframe the project around evidence-driven edge discovery rather than one fixed hypothesis.
- Keep the current recorder, replay, stream, and reporting code as shared infrastructure.
- Build a repeatable research workflow for objective-source market trading.
- Measure lead-lag between external source events and Polymarket repricing.
- Paper trade one-sided entries with explicit exit assumptions.
- Produce ranked market and source-type outputs that support later go or no-go decisions.
- Preserve clean upgrade points for structural arbitrage, market making, and authenticated execution later.

## Non-Goals

- Real-money trading in the next phase
- Generic "trade all breaking news" automation
- Social-signal or wallet-following strategies
- Immediate maker quoting and inventory warehousing
- Immediate multi-venue expansion
- Trying to rescue full-set arbitrage by threshold tuning alone

## Constraints And Assumptions

- Venue remains Polymarket only.
- The next phase should stay focused on binary `YES/NO` markets.
- A market is eligible only if the resolution path is explicit enough to map to a trustworthy source.
- Source timestamps must be auditable and preserved in artifacts.
- Signals must be reproducible from saved raw source payloads plus normalized market events.
- Entry and exit rules must be explicit; the system cannot quietly assume instant mark-to-market realization.
- Sports markets are not a good first taker domain because marketable orders are delayed by 3 seconds and resting books are cleared at game start.
- Most Polymarket markets remain fee-free; maker-rebate and liquidity-reward strategy work belongs in a later dedicated phase.
- The project should prefer objective and machine-readable source domains over subjective or narrative markets.

Important design constraint:

- the next phase must be able to produce a useful negative result

If the research shows that source updates do not create a repeatable tradable lag, the system should say so clearly rather than force a trading conclusion.

## Official References

These sources ground the design in current Polymarket docs as checked on 2026-03-20:

- [Markets & Events](https://docs.polymarket.com/concepts/markets-events)
- [Orderbook](https://docs.polymarket.com/trading/orderbook)
- [WebSocket Overview](https://docs.polymarket.com/market-data/websocket/overview)
- [Create Order](https://docs.polymarket.com/trading/orders/create)
- [Order Lifecycle](https://docs.polymarket.com/concepts/order-lifecycle)
- [Fees](https://docs.polymarket.com/polymarket-learn/trading/fees)
- [Liquidity Rewards](https://docs.polymarket.com/market-makers/liquidity-rewards)
- [Maker Rebates Program](https://docs.polymarket.com/market-makers/maker-rebates)
- [Negative Risk Markets](https://docs.polymarket.com/developers/neg-risk/overview)

## Proposed Approach

The recommended architecture is to keep the current event-driven market core and add a source-aware research layer above it.

High-level flow:

`Gamma metadata + Polymarket market stream + external objective sources -> normalized market events + normalized source events -> lead-lag analyzer -> signal evaluator -> one-sided paper execution -> ranked research artifacts`

Why this approach:

- it keeps the proven infrastructure
- it makes the edge hypothesis explicit and testable
- it narrows the market universe before deeper execution work
- it creates reusable building blocks for later structure-arb and maker strategies

Alternatives considered and rejected for the next phase:

1. Keep optimizing full-set arbitrage
   Rejected because the latest live study showed no raw edge in the tested universe. Better accounting will improve truthfulness, not create profit.

2. Jump directly to maker quoting
   Rejected as the immediate next phase because it requires authentication, order management, queue risk, inventory management, and reward-aware pricing before the project has a validated edge thesis for where to quote.

3. Build a generic news or NLP trader
   Rejected because it invites ambiguity, irreproducible signals, and poor post-mortem quality. The project should earn complexity only after succeeding on objective-source domains first.

## System Overview

The platform is now best understood as three layers:

1. Shared market-data and replay infrastructure
2. Strategy research modules
3. Execution and operational modules

### 1. Shared Infrastructure

This is the reusable core that already exists in some form and should remain strategy-agnostic:

- market catalog loading
- metadata refresh
- live market-data adapters
- recording and replay
- normalized state store
- artifact writing
- feed-health and latency instrumentation

### 2. Strategy Research Modules

These are the edge-specific layers that sit on top of the shared core:

- full-set arbitrage study tools
- market-quality ranking
- objective-source event research
- later, structure-arb research
- later, maker/reward research

### 3. Execution And Operations

These layers should stay behind research until a strategy is validated:

- one-sided paper execution and exit accounting
- authenticated order entry
- user-channel state reconciliation
- runtime kill switches
- alerts, reconnect, and deployment controls

## Detailed Next Phase: Phase 2.3 Objective-Source Event Research

### Purpose

Determine whether Polymarket markets tied to explicit external sources exhibit a repeatable lag between source updates and market repricing that is large enough to support one-sided paper trading after costs and depth constraints.

### Core Research Question

For a market with a clear resolution source, when the source emits a state change that should move fair value, does Polymarket's order book lag long enough to create an executable entry?

The answer must be measurable through saved artifacts, not intuition.

### Scope

This phase covers:

- broader candidate-market discovery
- source-aware market metadata
- external source ingestion
- source-to-market mapping
- lead-lag measurement
- one-sided event-driven paper entries and exits
- ranked research outputs

This phase does not cover:

- authenticated live trading
- passive maker quoting
- generic unstructured news ingestion
- multi-market structural baskets
- automatic production deployment

### Market Eligibility Rules

A market is eligible for Phase 2.3 only if all of the following hold:

- the market is binary and orderbook-enabled
- the resolution rule is explicit enough to identify a canonical source
- the source update can be timestamped precisely enough for lag analysis
- the mapping from source event to expected `YES` or `NO` move is deterministic enough to audit
- the market is not in a domain with mechanics that invalidate the intended entry style

Early inclusion categories:

- official filings or notices
- exchange or protocol status pages
- onchain contract events with canonical indexing
- scheduled numeric releases from official publishers

Early exclusion categories:

- narrative politics with ambiguous timing
- celebrity or rumor-driven markets
- sports taker trading
- markets whose resolution depends on subjective interpretation across many sources

### Deliverables

By the end of Phase 2.3, the system should produce:

- an expanded candidate market catalog with source metadata
- a source registry that maps markets to parsers and confidence rules
- normalized source-event artifacts with raw payload retention
- market response studies that measure lag, size, and price reaction
- one-sided paper-trading artifacts for accepted and rejected signals
- ranked market and source-type summaries for later selection

### Core Components

### 1. Candidate Market Expansion And Metadata Enrichment

Purpose:

- expand the market universe beyond the current handpicked allowlist
- capture the metadata required to determine whether a market is source-eligible

Responsibilities:

- ingest a broader set of active markets from Gamma
- store category, end date, status, fee flags, event slug, question text, and resolution text
- attach preliminary tags such as `objective_source_candidate`, `sports`, `crypto`, `ambiguous_resolution`, or `manual_review_required`
- support ranking and filtering before any trading logic runs

This component should answer:

- which markets are even candidates for objective-source research

### 2. Resolution And Source Registry

Purpose:

- hold the authoritative mapping from market to external source and signal logic

Responsibilities:

- define the source type, source URL or endpoint, parser identifier, and confidence rules for each tracked market
- encode whether a source event implies a `YES` move, a `NO` move, or a terminal outcome
- record invalidation rules such as ambiguous wording, missing official publication time, or multi-source dependencies
- keep human-maintained overrides explicit rather than hidden inside code

This registry is the heart of the phase. If the mapping is weak, the strategy is weak.

### 3. External Source Adapters

Purpose:

- ingest objective external updates in a normalized and replayable format

Responsibilities:

- poll or subscribe to approved external sources
- persist raw payloads with local receipt timestamps
- parse normalized source events with source-side timestamps when available
- classify parse failures, source downtime, and stale-source conditions
- support replay from captured source artifacts

The system should start with a small number of source families rather than a giant adapter zoo.

### 4. Lead-Lag And Market Response Tracker

Purpose:

- measure how Polymarket responds after a source event

Responsibilities:

- align normalized source events with Polymarket order-book state
- capture pre-event and post-event price and depth snapshots
- compute lag metrics such as:
  - time to first visible move
  - time to threshold crossing
  - best executable entry within a response window
  - maximum favorable move
  - time until edge disappears
- distinguish between "source was early" and "market was already priced"

This component is the main research engine for deciding whether a source class is promising.

### 5. Signal Evaluator

Purpose:

- decide whether a given source event warrants a one-sided paper trade

Entry logic should require all of the following:

- source confidence passes the configured threshold
- mapping from source event to market direction is unambiguous
- market is open, active, and not too close to resolution or halt conditions
- visible size and expected depth support the intended entry
- expected edge after fees, slippage, and operational buffer clears the configured minimum
- the signal has not already become stale because the market fully repriced

The evaluator should emit both:

- accepted signals
- rejected signals with explicit reasons

### 6. One-Sided Paper Execution And Exit Lifecycle

Purpose:

- simulate what would have happened if the bot had acted on an accepted source event

Responsibilities:

- enter a directional `YES` or `NO` position using configured marketable execution assumptions
- model depth-aware entry price and slippage
- support explicit exit modes:
  - exit on repricing target
  - exit on time stop
  - hold to resolution when the source event is effectively terminal
- track capital lock-up and exit uncertainty honestly
- classify late entries, partial exits, and stale exits separately from successful trades

This is intentionally still paper-only, but it must be honest enough to support later go or no-go decisions.

### 7. Research Artifacts And Ranking

Purpose:

- make Phase 2.3 useful even when many markets fail

Required outputs:

- run summary
- enriched market catalog snapshot
- source event log
- signal decision log
- trade log
- rejection log
- per-market response summary
- per-source-type ranking summary
- feed-health and source-health counters

The ranking should prioritize:

- repeatable lead-lag
- executable size
- post-cost edge
- signal clarity
- operational reliability of the source

## Data Model

The next implementation plan should define stable contracts for at least the following records.

### Enriched Market Entry

- market identifier
- event slug
- question text
- category or tags
- end date
- fee metadata
- resolution text
- eligibility status
- source registry key

### Source Event

- source event identifier
- source type
- source URL or origin
- source-side timestamp if present
- local receipt timestamp
- normalized event payload
- raw payload reference
- parse confidence
- affected market identifiers

### Market Response Window

- market identifier
- linked source event identifier
- pre-event best bid and ask
- pre-event depth snapshot
- first market move timestamp
- best executable entry seen in the configured window
- best favorable move after entry
- time to repricing
- final classification

### Signal Decision

- market identifier
- source event identifier
- direction (`YES` or `NO`)
- estimated fair-value shift or trigger class
- expected entry price
- expected edge after costs
- decision outcome
- rejection reason if applicable

### Directional Paper Trade

- run identifier
- market identifier
- source event identifier
- direction
- entry timestamp
- entry price and size
- exit mode
- exit timestamp
- exit price
- realized or modeled PnL
- lifecycle classification

## CLI And Workflow Expectations

The next implementation plan should add dedicated research commands rather than overloading the original arbitrage commands.

Expected workflow:

1. refresh and enrich a broader market catalog
2. build or update the source registry
3. record or ingest source events alongside market events
4. run lead-lag studies over a configured universe
5. run one-sided paper simulations on accepted signals
6. produce ranked outputs for shortlist creation

Likely command shape:

- catalog expansion and enrichment command
- source-event study command
- event-paper command
- replay analysis command for recorded source plus market runs

Exact command names can be finalized in the implementation plan.

## Entry, Exit, And Risk Rules

### Entry Rules

The next phase should be conservative by default:

- no trade without a clear source mapping
- no trade if the market already fully repriced
- no trade if visible depth is too small
- no trade in the final moments before resolution unless explicitly supported by the source model
- no averaging down

### Exit Rules

Each strategy configuration must choose one of these explicitly:

- target repricing exit
- time-based exit
- hold to resolution

The artifact set must record which exit logic was used so later comparisons remain honest.

### Required Risk Controls

- max capital per market
- max capital per source family
- max concurrent directional positions
- stale-source rejection
- stale-market rejection
- ambiguity kill switch
- cooldown after a source event for the same market
- hard disable for unsupported categories

## Error Handling And Failure Classification

Phase 2.3 should classify failures rather than folding them into generic "missed trade" buckets.

Required classifications:

- ambiguous source mapping
- parser failure
- source unavailable
- source stale
- market already repriced
- insufficient entry depth
- insufficient exit depth
- market closed, halted, or resolved
- fee or tick-size mismatch
- signal conflict across sources
- replay corruption or missing source artifact

## Testing Strategy

The next implementation plan should include:

### Unit Tests

- source parser normalization
- source-to-market mapping
- signal evaluation thresholds
- lead-lag metric calculation
- entry and exit accounting

### Deterministic Replay Tests

- identical source plus market artifacts produce identical signal decisions
- the same source event cannot trigger duplicate entries without an explicit policy
- stale-source and stale-market gating behaves predictably

### Failure-Mode Tests

- official source payload arrives but does not parse
- source event is valid but the market already moved
- direction mapping is ambiguous and the signal is rejected
- exit liquidity is too thin to realize the paper result cleanly

### Acceptance Scenarios

- one objective-source market produces an accepted signal and a profitable paper exit
- one market produces only rejected signals with correct reasons
- one market shows no measurable lag and is classified as unpromising

## Success Criteria For Phase 2.3

Phase 2.3 should be considered successful if it can:

- identify a non-trivial set of objective-source candidate markets
- ingest and replay external source events alongside Polymarket market data
- measure lead-lag and executable depth in a repeatable way
- produce honest one-sided paper-trading artifacts
- rank markets and source classes by observed post-cost edge quality
- make it obvious whether event-driven trading deserves further investment

Important success condition:

- a defensible negative result is still a successful phase outcome

If Phase 2.3 shows no repeatable source-led edge, that is valuable evidence and should redirect the project toward structural arbitrage or passive maker research instead of wasting more effort.

## Future Phase Roadmap

These phases are intentionally high level. Only Phase 2.3 is detailed in this document.

### Phase 2.4: Event Execution Realism And Exit Accounting

- improve one-sided fill realism
- model partial exits and holding costs more honestly
- refine lifecycle accounting for hold-to-resolution positions
- add deeper rejection and slippage diagnostics

### Phase 3: Structural Relationship Research

- expand from single-market event trading into cross-market relationships
- scan for logical inconsistencies across mutually exclusive or linked markets
- add negative-risk and basket-style research where market structure supports it

### Phase 4: Passive Maker And Incentive Research

- study fee-enabled markets with maker rebates
- study liquidity-reward-adjusted profitability for passive quoting
- build quote-quality, inventory, and reward-scoring analytics before any live maker deployment

### Phase 5: Authenticated Execution And Safety Rails

- add authenticated order entry, cancels, and user-stream reconciliation
- implement hard kill switches, exposure controls, and audit logs
- require strategy-specific readiness gates before enabling live orders

### Phase 6: Small-Capital Live Rollout

- deploy only strategies that already survived replay and paper research
- start with tiny size
- require manual oversight, alerting, reconnect hardening, and daily review artifacts

### Phase 7: Multi-Strategy Portfolio Layer

- allocate capital across validated strategy families
- compare event-driven, structural, and passive-maker books on a common reporting basis
- rotate markets and source families based on measured performance and operational quality

## Planning Handoff

This spec is ready to hand off to an implementation-planning step focused on Phase 2.3 only.

The next plan should:

- treat the current recorder and replay stack as foundational
- avoid authenticated trading work
- keep the initial source universe small and auditable
- produce concrete tasks for metadata enrichment, source ingestion, lead-lag analysis, directional paper trading, and ranked artifacts

Later phases should remain high-level until Phase 2.3 produces evidence worth building on.
