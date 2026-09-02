"""
ATLAS Dry-Run Trading Loop.

Connects market snapshots to the ATLAS intelligence and execution
layers while keeping all trading strictly simulated.
"""

from dataclasses import dataclass

from atlas.algorithms.base import Action, AlgorithmSignal
from atlas.algorithms.orchestrator import DecisionOrchestrator
from atlas.algorithms.pipeline import AlgorithmPipeline
from atlas.algorithms.registry import AlgorithmRegistry
from atlas.algorithms import (
    IntradayMomentumAlgorithm,
    IntradayTrendAlgorithm,
    IntradayBreakoutAlgorithm,
    IntradayMeanReversionAlgorithm,
    IntradayVWAPAlgorithm,
    IntradayValueZoneAlgorithm,
)
from atlas.agents.base import AgentObservation
from atlas.agents.intelligence import MarketIntelligence
from atlas.trading.dry_run_trader import DryRunResult, DryRunTrader
from atlas.trading.expected_return_service import ExpectedReturnService
from atlas.trading.market_data import MarketSnapshot
from atlas.adapters.binance_market_data import BinanceMarketData


@dataclass(frozen=True, slots=True)
class DryRunCycleResult:
    symbol: str
    price: float
    observations: tuple[AgentObservation, ...]
    intelligence_score: float
    intelligence_confidence: float
    algorithm_signals: tuple[AlgorithmSignal, ...]
    decision: object
    expected_return: float | None
    execution: DryRunResult


class DryRunLoop:
    """
    One-cycle ATLAS dry-run pipeline.

    Market data -> agents -> intelligence -> orchestrator -> expected
    return -> trading cost gate -> paper execution.
    """

    def __init__(
        self,
        agents,
        intelligence: MarketIntelligence | None = None,
        orchestrator: DecisionOrchestrator | None = None,
        trader: DryRunTrader | None = None,
        algorithm_pipeline: AlgorithmPipeline | None = None,
        expected_return_service: ExpectedReturnService | None = None,
    ):
        self.agents = tuple(agents)
        self.intelligence = intelligence or MarketIntelligence()
        self.trader = trader or DryRunTrader()
        self.expected_return_service = expected_return_service
        self.algorithm_pipeline = (
            algorithm_pipeline or self._default_algorithm_pipeline()
        )
        self.orchestrator = (
            orchestrator
            or DecisionOrchestrator(
                algorithm_pipeline=self.algorithm_pipeline,
            )
        )

    @staticmethod
    def _default_algorithm_pipeline() -> AlgorithmPipeline:
        registry = AlgorithmRegistry()

        for algorithm in (
            IntradayMomentumAlgorithm(),
            IntradayTrendAlgorithm(),
            IntradayBreakoutAlgorithm(),
            IntradayMeanReversionAlgorithm(),
            IntradayVWAPAlgorithm(),
            IntradayValueZoneAlgorithm(),
        ):
            registry.register(algorithm)

        return AlgorithmPipeline(registry)

    def process(self, snapshot: MarketSnapshot) -> DryRunCycleResult:
        observations = tuple(
            self._observe_agent(agent, snapshot)
            for agent in self.agents
        )

        intelligence = self.intelligence.analyze(
            snapshot.symbol,
            list(observations),
        )

        market_data = {
            "price": snapshot.price,
            "candles": [
                {
                    "timestamp": candle.timestamp,
                    "open": candle.open,
                    "high": candle.high,
                    "low": candle.low,
                    "close": candle.close,
                    "volume": candle.volume,
                }
                for candle in snapshot.candles
            ],
        }

        algorithm_signals = self.algorithm_pipeline.generate_signals(
            snapshot.symbol,
            market_data,
        )

        intelligence_signal = self._signals_from_intelligence(
            snapshot,
            intelligence,
        )

        orchestration = self.orchestrator.decide(
            snapshot.symbol,
            intelligence_signal,
            observations=list(observations),
            market_data=market_data,
        )

        decision = orchestration.decision
        expected_return = self._estimate_expected_return(
            snapshot.symbol,
            decision,
        )

        execution = self.trader.process_signal(
            symbol=snapshot.symbol,
            action=decision.action,
            price=snapshot.price,
            confidence=decision.confidence,
            risk_score=decision.risk_score,
            reason=decision.reason,
            expected_return=expected_return,
        )

        return DryRunCycleResult(
            symbol=snapshot.symbol,
            price=snapshot.price,
            observations=observations,
            intelligence_score=intelligence.score,
            intelligence_confidence=intelligence.confidence,
            algorithm_signals=tuple(algorithm_signals),
            decision=decision,
            expected_return=expected_return,
            execution=execution,
        )

    def process_binance(
        self,
        adapter,
        symbol: str,
        interval: str = "1m",
        limit: int = 100,
    ) -> DryRunCycleResult:
        """Fetch a Binance snapshot and process it through dry-run."""
        market_data = BinanceMarketData(adapter)
        snapshot = market_data.snapshot(
            symbol=symbol,
            interval=interval,
            limit=limit,
        )
        return self.process(snapshot)

    def _estimate_expected_return(self, symbol: str, decision) -> float | None:
        """Estimate expected return when the historical service is configured."""
        if self.expected_return_service is None:
            return None

        action = Action(str(decision.action.value).upper())
        return self.expected_return_service.estimate(
            symbol=symbol,
            action=action,
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
