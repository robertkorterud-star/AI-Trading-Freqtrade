"""
ATLAS Dry-Run Trading Loop.

Connects market snapshots to the ATLAS intelligence and execution
layers while keeping all trading strictly simulated.
"""

from dataclasses import dataclass

from atlas.algorithms.base import Action, AlgorithmSignal
from atlas.algorithms.orchestrator import DecisionOrchestrator
from atlas.agents.base import AgentObservation
from atlas.agents.intelligence import MarketIntelligence
from atlas.trading.dry_run_trader import DryRunResult, DryRunTrader
from atlas.trading.market_data import MarketSnapshot


@dataclass(frozen=True, slots=True)
class DryRunCycleResult:
    symbol: str
    price: float
    observations: tuple[AgentObservation, ...]
    intelligence_score: float
    intelligence_confidence: float
    decision: object
    execution: DryRunResult


class DryRunLoop:
    """
    One-cycle ATLAS dry-run pipeline.

    Market data -> agents -> intelligence -> orchestrator -> trader.
    """

    def __init__(
        self,
        agents,
        intelligence: MarketIntelligence | None = None,
        orchestrator: DecisionOrchestrator | None = None,
        trader: DryRunTrader | None = None,
    ):
        self.agents = tuple(agents)
        self.intelligence = intelligence or MarketIntelligence()
        self.orchestrator = orchestrator or DecisionOrchestrator()
        self.trader = trader or DryRunTrader()

    def process(self, snapshot: MarketSnapshot) -> DryRunCycleResult:
        observations = tuple(
            self._observe_agent(agent, snapshot)
            for agent in self.agents
        )

        intelligence = self.intelligence.analyze(
            snapshot.symbol,
            list(observations),
        )

        signals = self._signals_from_intelligence(
            snapshot,
            intelligence,
        )

        orchestration = self.orchestrator.decide(
            snapshot.symbol,
            signals,
            observations=list(observations),
        )

        decision = orchestration.decision

        execution = self.trader.process_signal(
            symbol=snapshot.symbol,
            action=decision.action,
            price=snapshot.price,
            confidence=decision.confidence,
            risk_score=decision.risk_score,
            reason=decision.reason,
        )

        return DryRunCycleResult(
            symbol=snapshot.symbol,
            price=snapshot.price,
            observations=observations,
            intelligence_score=intelligence.score,
            intelligence_confidence=intelligence.confidence,
            decision=decision,
            execution=execution,
        )

    @staticmethod
    def _observe_agent(agent, snapshot: MarketSnapshot) -> AgentObservation:
        """
        Produce an observation from an ATLAS agent.

        Native ATLAS agents implement observe(). Older/simple test
        agents may implement analyze(). Support both contracts so the
        dry-run loop remains backwards compatible.
        """

        observe = getattr(agent, "observe", None)

        if observe is not None:
            return observe(
                snapshot.symbol,
                {
                    "snapshot": snapshot,
                    "price": snapshot.price,
                    "candles": snapshot.candles,
                },
            )

        analyze = getattr(agent, "analyze", None)

        if analyze is not None:
            return analyze(snapshot)

        raise TypeError(
            f"Agent {agent!r} must implement observe() or analyze()"
        )

    @staticmethod
    def _signals_from_intelligence(
        snapshot,
        intelligence,
    ):
        if intelligence.direction == "bullish":
            action = Action.BUY
        elif intelligence.direction == "bearish":
            action = Action.SELL
        else:
            action = Action.HOLD

        return [
            AlgorithmSignal(
                algorithm="market_intelligence",
                symbol=snapshot.symbol,
                timeframe="multi",
                action=action,
                score=intelligence.score,
                confidence=intelligence.confidence,
            )
        ]
