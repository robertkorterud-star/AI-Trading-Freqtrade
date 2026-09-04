# ATLAS — AI Investment & Trading Platform

ATLAS is a **standalone, modular AI investment and trading platform**.

It is designed to be **broker- and execution-engine-independent**. ATLAS can analyze markets, combine specialized intelligence, make explainable decisions, apply risk and portfolio constraints, learn from outcomes, and hand approved decisions to an external execution adapter.

## Architecture

```text
MARKET DATA
     ↓
Normalized MarketData
     ↓
Intelligence / Signal Layer
     ↓
Signal Ensemble
     ↓
Decision Engine
     ↓
Risk Management
     ↓
Portfolio Manager
     ↓
Execution Engine
     ↓
Broker / Exchange
```

Core principles:

- Specialized components have one clear responsibility.
- Algorithms produce signals and evidence, not trades.
- The Decision Engine owns the final trading decision.
- Risk Management can veto or constrain decisions.
- Portfolio Management controls aggregate exposure and allocation.
- Execution is isolated behind external broker/exchange interfaces.
- Decisions and important intelligence are explainable and testable.
- External providers are accessed through replaceable adapters.

## Current platform capabilities

ATLAS already contains substantial infrastructure for:

- Market-data adapters and normalized market data
- Technical, momentum, trend and price-action intelligence
- News, company and broader intelligence analysis
- AI/Ollama and external research adapters
- Analyst/agent registries and analysis pipelines
- Signal and decision processing
- Decision Engine integration
- Portfolio assessment and allocation constraints
- Prediction/strategy learning components
- Dashboard and supporting interfaces

Development continues incrementally with a strong rule: **do not create a new module when an existing component already owns the responsibility**.

## Freqtrade boundary

Historical Freqtrade code may remain in the repository as project context, but **Freqtrade is not part of the target ATLAS architecture** and is not required by the ATLAS runtime.

ATLAS must remain independently installable, testable and runnable.

## Development

The Python package is defined in `pyproject.toml`. Run the test suite with:

```bash
pytest -q
```

Before adding a capability:

1. Search the repository for an existing implementation.
2. Identify the current owner of the responsibility.
3. Reuse existing models and interfaces where appropriate.
4. Extend an existing component when the responsibility already belongs there.
5. Create a new module only when the responsibility is genuinely independent.
6. Add tests for every new capability.

## Project status

ATLAS is under active incremental development. The repository contains both the current standalone ATLAS platform and historical project material; the architecture documentation defines the intended standalone boundary.
