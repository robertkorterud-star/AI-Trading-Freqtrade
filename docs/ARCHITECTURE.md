# ATLAS Architecture

## Vision

ATLAS is a standalone, modular AI investment and trading platform.

ATLAS is designed to become broker- and execution-engine independent. Historical Freqtrade code is project context, not part of the target ATLAS architecture.

The goal is not to build a single AI model. The goal is to build a team of specialized intelligence components that cooperate to make explainable investment and trading decisions.

---

# System Overview

```text
                         ATLAS
                           │
                    ┌──────▼──────┐
                    │ Decision Core│
                    └──────┬──────┘
                           │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
   Technical           Momentum            AI / ML
     Signal             Signal              Signal
        │                  │                  │
        └──────────────────┼──────────────────┘
                           ▼
                    Signal Ensemble
                           │
                    Decision Engine
                           │
                    Risk Management
                           │
                    Portfolio Manager
                           │
                    Execution Engine
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
           Broker       Exchange      Nordnet
```

Algorithms and intelligence components produce signals and evidence. They do not execute trades.

The Decision Engine remains the central decision authority. Signal ensembles provide structured evidence and are not a second decision engine.

---

# Core Principles

- Every component has one responsibility.
- Algorithms produce signals, not trades.
- The Decision Engine owns the final trading decision.
- Risk management can veto or constrain decisions.
- Portfolio management controls aggregate exposure.
- Execution is isolated behind broker/exchange interfaces.
- Every decision must be explainable.
- Components must be independently testable.
- Everything important is logged.
- External providers must be replaceable through adapters.

---

# Market Data Layer

ATLAS receives normalized market data through a provider interface.

```text
Market Data Provider
        │
        ├── YFinance (current adapter)
        ├── EODHD (future adapter)
        ├── Twelve Data (future adapter)
        ├── Euronext (future adapter)
        └── Broker / Exchange providers (future)
```

Provider-specific details must remain inside adapters. Intelligence components consume normalized ATLAS market data.

---

# Intelligence Layer

## Technical Signal

Purpose:

Determine deterministic technical direction from the current market snapshot.

Current inputs include:

- Price
- MA20
- MA50
- Volume ratio

MA20/MA50 determine the current directional signal. Volume supports confidence but does not create direction by itself.

Output:

- BUY
- SELL
- HOLD
- Confidence
- Reasons

---

## Momentum Signal

Purpose:

Measure buying and selling momentum without executing trades.

Planned inputs include:

- RSI
- MACD
- ADX
- EMA alignment

Output:

- Momentum signal
- Momentum score
- Confidence
- Reasons

Momentum is an independent contributor to the Signal Ensemble. It must not replace the Decision Engine.

---

## Volume Intelligence

Purpose:

Interpret whether market activity supports an existing directional signal.

Current inputs include:

- Volume
- Average volume
- Volume ratio

Volume Intelligence and Volume Confirmation are explanatory/supporting components. Volume alone does not create BUY or SELL direction.

---

## Volatility Intelligence

Purpose:

Measure market stability and trading risk.

Planned inputs include:

- ATR
- Bollinger Bands

Output:

- Volatility state
- Risk level
- Reasons

---

## Breakout Intelligence

Purpose:

Detect meaningful price breakouts using market structure and confirmation data.

Breakout detection is a signal contributor only. It does not execute trades.

---

# Signal Ensemble

The Signal Ensemble combines independent signal contributors such as:

- Technical Signal
- Momentum Signal
- AI/ML predictions
- Future specialized signals

It produces a normalized ensemble result with contributors and reasons.

The ensemble is advisory evidence for the Decision Engine, not a replacement for it.

---

# Decision Engine

The Decision Engine is the central authority for final trading decisions.

Responsibilities include:

- Combine evidence
- Evaluate intelligence signals
- Apply decision policy
- Incorporate learned information
- Produce BUY / SELL / HOLD
- Explain the decision

No individual indicator or algorithm is allowed to become the final trader on its own.

---

# Risk Management

Risk Management protects capital independently from signal generation.

Responsibilities include:

- Position sizing
- Stop loss
- Take profit
- Daily loss limits
- Maximum exposure
- Drawdown protection
- Emergency stops

Risk controls can restrict or veto otherwise valid trading signals.

---

# Portfolio Management

Portfolio Management evaluates decisions at portfolio level.

Responsibilities include:

- Asset exposure
- Correlation
- Open positions
- Allocation
- Diversification
- Rebalancing

---

# Execution Engine

The Execution Engine is responsible for turning an approved ATLAS decision into an order through an external execution adapter.

```text
ATLAS Decision
      │
      ▼
Execution Engine
      │
      ├── Exchange Adapter
      ├── Broker Adapter
      └── Future Nordnet Adapter
```

Execution must remain separate from signal generation and decision logic.

---

# Learning System

ATLAS continuously evaluates predictions and decisions against actual outcomes.

The learning system can use:

- Historical trades
- Prediction evaluations
- Backtesting
- Experiments
- Market regimes
- Algorithm performance

Future learning can dynamically adjust the influence of signal contributors based on measured performance, while remaining constrained by risk management.

---

# Future Intelligence Departments

The long-term ATLAS platform may contain specialized intelligence components for:

- Fundamental analysis
- News
- Sentiment
- Macro analysis
- On-chain analysis
- Insider activity
- Mean reversion
- Scalping
- Day trading
- Research

These components must be added only when a clearly defined responsibility is missing from the existing architecture.

---

# Development Rule: Avoid Duplication

Before creating a new component:

1. Search the repository for existing implementations.
2. Identify the current owner of the responsibility.
3. Reuse existing data models and interfaces where possible.
4. Extend an existing component when the responsibility already belongs there.
5. Create a new component only when it represents a genuinely independent responsibility.
6. Add tests with every new capability.

This rule is especially important for technical indicators and trading signals.

---

# Target Architecture

```text
MARKET DATA
     │
     ▼
Normalized MarketData
     │
     ▼
Intelligence / Signal Layer
     │
     ├── Technical Signal
     ├── Momentum Signal
     ├── Volume Intelligence
     ├── Volatility Intelligence
     ├── Breakout Intelligence
     └── AI / ML Signals
     │
     ▼
Signal Ensemble
     │
     ▼
Decision Engine
     │
     ▼
Risk Management
     │
     ▼
Portfolio Manager
     │
     ▼
Execution Engine
     │
     ▼
Broker / Exchange
```

## Long-Term Goal

Build ATLAS into a standalone, explainable AI investment platform where every decision can be traced from market evidence through signal generation, ensemble reasoning, decision policy, risk controls, portfolio constraints and execution.