# ATLAS Architecture

## Vision

ATLAS is a modular multi-agent AI trading engine built on top of Freqtrade.

The goal is not to build a single AI model.

The goal is to build a team of specialized AI agents that cooperate to make trading decisions.

---

# System Overview

Freqtrade

↓

AITraderPro Strategy

↓

ATLAS Engine

↓

AI Agents

↓

Trade Decision

---

# Core Principles

- Every agent has one responsibility.
- Every decision must be explainable.
- AI supports decisions but does not replace risk management.
- Components must be independently testable.
- Everything is logged.

---

# Agent Overview

## Market Agent

Purpose:

Determine overall market trend.

Input:

- EMA
- Market structure
- Higher timeframe trend

Output:

Bullish

Bearish

Sideways

Confidence score

---

## Momentum Agent

Purpose:

Measure buying/selling pressure.

Input:

- RSI
- MACD
- ADX
- EMA alignment

Output:

Momentum Score

---

## Volume Agent

Purpose:

Validate moves using volume.

Input:

- Volume
- OBV
- VWAP

Output:

Volume Score

---

## Volatility Agent

Purpose:

Determine market stability.

Input:

- ATR
- Bollinger Bands

Output:

Risk Level

---

## Risk Agent

Purpose:

Protect capital.

Responsibilities:

Position sizing

Stop Loss

Take Profit

Daily loss limit

Maximum exposure

---

## Portfolio Agent

Purpose:

Manage total portfolio risk.

Responsibilities:

Coin exposure

Correlation

Open positions

---

## Learning Agent (Future)

Purpose:

Analyze historical trades.

Find patterns.

Suggest improvements.

---

## News Agent (Future)

Purpose:

Analyze news sentiment.

Sources:

News

Reddit

Fear & Greed

Social media

---

## Decision Agent

Purpose:

Collect all agent outputs.

Calculate final Trade Score.

Generate:

BUY

SELL

HOLD

---

# Engine

The Engine coordinates every agent.

Workflow

Market Data

↓

Indicators

↓

Agents

↓

Decision

↓

Freqtrade

---

# Long-Term Goal

Create an explainable AI trading platform where every decision can be traced back to measurable evidence.