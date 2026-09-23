# ATLAS Professional Investment & Trading Roadmap

## Purpose

Build ATLAS as a multi-asset investment and trading intelligence platform that can support long-term investing, swing/short-term trading, day trading, scalping, long and short exposure, equities, ETFs and crypto without creating parallel decision engines.

The existing canonical flow remains authoritative:

MARKET DATA
→ Normalized MarketData
→ Intelligence / Signal Layer
→ Signal Ensemble
→ Decision Engine
→ Risk Management
→ Portfolio Manager
→ Execution Engine
→ Broker / Exchange

Opportunity discovery is research/evidence only. It must never become a second DecisionEngine.

## What professional workflows have in common

Current institutional workflow references from Bloomberg and LSEG consistently connect:

- market/reference data
- research and news
- quantitative analytics
- opportunity discovery
- portfolio construction
- pre-trade risk
- execution/liquidity
- post-trade/TCA
- performance attribution and learning

ATLAS should follow the same separation of responsibilities at a smaller, modular scale.

## Target ATLAS workflow

MARKET DATA
→ Market Context
→ Opportunity Discovery
→ Candidate Pool
→ Candidate Ranking
→ Intelligence
→ Signal Ensemble
→ DecisionEngine
→ Risk
→ Portfolio
→ Execution
→ Post-trade / TCA
→ Prediction & Outcome Tracking
→ Learning

## Opportunity Discovery

The existing repository already contains:

- AssetUniverse
- AssetDiscoveryService
- CandidateSelector
- CandidatePool
- MarketDiscoverySource
- AIResearchSource
- CandidateResearchService
- CandidateDecisionRanker
- CandidateSelectionReport

These are the existing owners for candidate discovery/ranking. Do not create a parallel scanner.

The existing discovery layer should evolve into a broader Opportunity Engine.

### Opportunity Engine responsibilities

It should answer:

"What assets deserve deeper ATLAS analysis now, and why?"

It should not answer:

"Should ATLAS execute this trade?"

## Candidate evidence

Candidate discovery should eventually be able to combine, where data is available:

### Market activity
- relative volume
- volume acceleration
- volatility expansion
- price acceleration
- range expansion
- liquidity
- spread
- market depth

### Technical structure
- trend
- momentum
- VWAP
- support/resistance
- breakout
- mean reversion
- ATR
- multi-timeframe agreement

### Fundamental / long-term
- earnings
- revenue/growth
- profitability/quality
- valuation
- estimates/revisions
- balance-sheet context

### Information / catalyst
- company news
- filings
- earnings events
- macro events
- sector/theme news
- sentiment

### Market context
- asset class
- market session
- market regime
- sector/index regime
- volatility regime
- liquidity regime

### Digital assets
- BTC regime
- funding
- open interest
- liquidations
- exchange liquidity
- on-chain evidence
- crypto-specific news

## Time horizons

The same candidate may be relevant to different horizons.

ATLAS should support at least:

- LONG_TERM
- SWING
- SHORT_TERM
- DAY_TRADE
- SCALP

A horizon is context for analysis and ranking. It is not a separate decision engine.

Example:

NVDA
- long-term: fundamental/quality opportunity
- swing: trend/momentum opportunity
- day trade: catalyst/RVOL/opening-structure opportunity

BTC
- long-term: macro/on-chain opportunity
- swing: regime/momentum opportunity
- day trade: volatility/liquidity opportunity
- scalp: microstructure/liquidity opportunity

## Long and short

The architecture must remain direction-neutral until the canonical DecisionEngine evaluates the evidence.

Candidate discovery can surface:

- bullish opportunity
- bearish opportunity
- neutral/monitor opportunity

Final LONG/SHORT/HOLD/EXIT remains owned by DecisionEngine and constrained by RiskManager.

## Equity session awareness

For US equities, ATLAS should distinguish at least:

- PREMARKET
- OPEN_AUCTION
- EARLY_SESSION
- MID_SESSION
- POWER_HOUR
- CLOSE_AUCTION
- AFTER_HOURS

Session information is context, not a trade signal.

NYSE currently describes a 9:30 ET core opening auction and a 4:00 ET closing auction, with opening imbalance information published before the opening auction. ATLAS should treat these as market-context inputs when appropriate, not as automatic entry rules.

## Crypto session awareness

Crypto is continuous, but ATLAS should still model:

- time-of-day activity
- regional/market overlap
- liquidity regime
- volatility regime
- activity spikes

There is no need to invent an artificial "market open" for crypto.

## Ranking

Candidate ranking should remain explainable.

The repository already has CandidateDecisionRanker and CandidateRankingEvidence.

Ranking should eventually distinguish:

1. discovery relevance
2. decision quality
3. regime fit
4. expected return after costs
5. risk-adjusted opportunity
6. execution/liquidity quality

Ranking is not permission to trade.

## Execution and post-trade

Professional workflows place explicit emphasis on execution quality and transaction-cost analysis.

ATLAS should eventually record:

- spread
- slippage
- estimated vs actual execution
- timing
- liquidity conditions
- trading costs
- market impact where measurable

PredictionTracker and OutcomeTracker remain the existing lifecycle owners for prediction/outcome measurement.

## Learning

ATLAS should eventually measure performance by:

- asset
- asset class
- horizon
- strategy/setup
- market regime
- volatility regime
- liquidity
- time of day
- catalyst type
- signal combination
- execution quality

This should allow ATLAS to learn where its own evidence is actually useful instead of assuming that a setup has an edge.

## Implementation order

### Phase 1 — Professional market context
- strengthen normalized market-data contracts
- multi-timeframe context
- session context
- volatility/liquidity context

### Phase 2 — Opportunity Engine
- strengthen existing AssetDiscoveryService
- preserve CandidatePool and existing discovery sources
- add explainable evidence rather than hard-coded trade rules
- support asset class and horizon context

### Phase 3 — Research intelligence
- news/catalyst integration
- fundamentals
- filings
- macro
- sector context
- crypto-specific intelligence

### Phase 4 — Strategy context
- long-term
- swing
- short-term
- day trading
- scalping
- long/short

These remain strategy contexts feeding the existing Intelligence/Signal/Decision architecture.

### Phase 5 — Execution intelligence
- liquidity-aware execution
- slippage tracking
- transaction-cost analysis
- execution feedback

### Phase 6 — Learning
- outcome attribution
- setup/regime statistics
- strategy-memory feedback
- adaptive evidence weighting based on measured results

## Development rule

Do not implement all phases at once.

For every phase:

1. inspect existing owner
2. reuse existing contracts
3. make the smallest architectural change
4. add focused tests
5. run the focused tests
6. run full pytest
7. inspect diff/status
8. only then continue

No scanner, strategy or AI component may become a parallel trading decision authority.
