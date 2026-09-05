"""
ATLAS Dry-Run Trading Loop.

Connects market snapshots to the ATLAS intelligence and execution
layers while keeping all trading strictly simulated.
"""

from dataclasses import dataclass
from datetime import datetime, timezone

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
from atlas.decision.engine import DecisionEngine
from atlas.portfolio.manager import PortfolioManager, PortfolioPosition
from atlas.risk.manager import RiskManager
from atlas.trading.dry_run_trader import DryRunResult, DryRunTrader
from atlas.trading.expected_return_service import ExpectedReturnService
from atlas.trading.indicator_engine import IndicatorEngine
from atlas.trading.market_data import MarketSnapshot
from atlas.trading.multi_timeframe_analysis import (
    MultiTimeframeAnalysis,
    MultiTimeframeAnalyzer,
)
from atlas.trading.prediction_signal_service import PredictionSignalService
from atlas.trading.signal_evidence import SignalEvidenceAnalyzer
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
    """One-cycle ATLAS dry-run pipeline."""

    def __init__(
        self,
        agents,
        intelligence: MarketIntelligence | None = None,
        orchestrator: DecisionOrchestrator | None = None,
        trader: DryRunTrader | None = None,
        algorithm_pipeline: AlgorithmPipeline | None = None,
        expected_return_service: ExpectedReturnService | None = None,
        prediction_signal_service: PredictionSignalService | None = None,
        indicator_engine: IndicatorEngine | None = None,
        signal_evidence_analyzer: SignalEvidenceAnalyzer | None = None,
        multi_timeframe_analyzer: MultiTimeframeAnalyzer | None = None,
        risk_manager: RiskManager | None = None,
        portfolio_manager: PortfolioManager | None = None,
    ):
        self.agents = tuple(agents)
        self.intelligence = intelligence or MarketIntelligence()
        self.trader = trader or DryRunTrader()
        self.expected_return_service = expected_return_service
        self.prediction_signal_service = prediction_signal_service
        self.indicator_engine = indicator_engine or IndicatorEngine()
        self.signal_evidence_analyzer = signal_evidence_analyzer or SignalEvidenceAnalyzer()
        self.multi_timeframe_analyzer = multi_timeframe_analyzer or MultiTimeframeAnalyzer()
        self.algorithm_pipeline = algorithm_pipeline or self._default_algorithm_pipeline()
        self.risk_manager = risk_manager or RiskManager()
        self.portfolio_manager = portfolio_manager or PortfolioManager(
            max_exposure_pct=self.risk_manager.max_exposure_pct,
            max_single_position_pct=self.risk_manager.max_position_pct,
        )
        self._peak_equity: float | None = None
        self.orchestrator = orchestrator or DecisionOrchestrator(
            decision_engine=DecisionEngine(
                risk_manager=self.risk_manager,
                portfolio_manager=self.portfolio_manager,
            ),
            algorithm_pipeline=self.algorithm_pipeline,
            risk_manager=self.risk_manager,
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
        observations = tuple(self._observe_agent(agent, snapshot) for agent in self.agents)
        intelligence = self.intelligence.analyze(snapshot.symbol, list(observations))
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

        fusion_result, algorithm_signals = self.algorithm_pipeline.analyze(
            snapshot.symbol,
            market_data,
        )

        prediction_signal = self._prediction_signal(
            snapshot,
            timeframe=(algorithm_signals[0].timeframe if algorithm_signals else None),
        )
        if prediction_signal is not None:
            algorithm_signals = [*algorithm_signals, prediction_signal]
            fusion_result = self.algorithm_pipeline.fusion.combine(algorithm_signals)

        intelligence_signal = self._signals_from_intelligence(snapshot, intelligence)
        equity, current_exposure_pct, drawdown_pct, positions = self._portfolio_context(
            snapshot
        )
        orchestration = self.orchestrator.decide(
            snapshot.symbol,
            intelligence_signal,
            observations=list(observations),
            algorithm_signals=algorithm_signals,
            fusion_result=fusion_result,
            price=snapshot.price,
            equity=equity,
            current_exposure_pct=current_exposure_pct,
            drawdown_pct=drawdown_pct,
            portfolio_positions=positions,
        )

        decision = orchestration.decision
        expected_return = self._estimate_expected_return(snapshot.symbol, decision)
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

    def _portfolio_context(
        self,
        snapshot: MarketSnapshot,
    ) -> tuple[float, float, float, tuple[PortfolioPosition, ...]]:
        """Build the canonical risk/portfolio context before a dry-run decision."""
        prices = {symbol: snapshot.price for symbol in self.trader.portfolio.positions}
        prices[snapshot.symbol] = snapshot.price
        equity = self.trader.portfolio.equity(prices)
        if self._peak_equity is None:
            self._peak_equity = equity
        else:
            self._peak_equity = max(self._peak_equity, equity)

        exposure_value = sum(
            position.quantity * prices.get(symbol, position.average_price)
            for symbol, position in self.trader.portfolio.positions.items()
        )
        exposure_pct = (exposure_value / equity * 100.0) if equity > 0.0 else 0.0
        drawdown_pct = (
            max(0.0, (self._peak_equity - equity) / self._peak_equity * 100.0)
            if self._peak_equity > 0.0
            else 0.0
        )
        positions = tuple(
            PortfolioPosition(
                symbol=symbol,
                market_value=position.quantity * prices.get(
                    symbol,
                    position.average_price,
                ),
            )
            for symbol, position in self.trader.portfolio.positions.items()
        )
        return equity, exposure_pct, drawdown_pct, positions

    def _prediction_signal(self, snapshot: MarketSnapshot, *, timeframe: str | None = None):
        if self.prediction_signal_service is None:
            return None

        indicators = self.indicator_engine.calculate([
            {
                "timestamp": candle.timestamp,
                "open": candle.open,
                "high": candle.high,
                "low": candle.low,
                "close": candle.close,
                "volume": candle.volume,
            }
            for candle in snapshot.candles
        ])

        timeframe_data = self._multi_timeframe_data(snapshot)
        multi_timeframe = self.multi_timeframe_analyzer.analyze(
            snapshot.symbol,
            timeframe_data,
        )
        evidence = self.signal_evidence_analyzer.analyze(indicators, multi_timeframe)

        return self.prediction_signal_service.predict(
            evidence,
            symbol=snapshot.symbol,
            timestamp=datetime.fromtimestamp(snapshot.timestamp, tz=timezone.utc),
            timeframe=timeframe,
        )

    def _multi_timeframe_data(self, snapshot: MarketSnapshot) -> dict[str, dict]:
        """Derive MTF trend/momentum from normalized snapshot candles."""
        result = {}
        neutral_mtf = MultiTimeframeAnalysis(
            symbol=snapshot.symbol,
            timeframes=[],
            overall_signal="WAIT",
            confidence=0.0,
            alignment=0.0,
            data_quality="MISSING",
        )
        for timeframe, candles in snapshot.timeframe_candles.items():
            indicators = self.indicator_engine.calculate([
                {
                    "timestamp": candle.timestamp,
                    "open": candle.open,
                    "high": candle.high,
                    "low": candle.low,
                    "close": candle.close,
                    "volume": candle.volume,
                }
                for candle in candles
            ])
            evidence = self.signal_evidence_analyzer.analyze(indicators, neutral_mtf)
            result[timeframe] = {
                "trend": evidence.trend,
                "momentum": evidence.momentum,
                "data_quality": indicators.data_quality,
                "data_available": True,
            }
        return result

    def process_binance(self, adapter, symbol: str, interval: str = "1m", limit: int = 100):
        """Fetch a Binance snapshot with all configured MTF candles and process it."""
        market_data = BinanceMarketData(adapter)
        snapshot = market_data.snapshot(
            symbol=symbol,
            interval=interval,
            limit=limit,
            timeframes=self.multi_timeframe_analyzer.TIMEFRAMES,
        )
        return self.process(snapshot)

    def _estimate_expected_return(self, symbol: str, decision) -> float | None:
        if self.expected_return_service is None:
            return None
        action = Action(str(decision.action.value).upper())
        return self.expected_return_service.estimate(symbol=symbol, action=action)

    @staticmethod
    def _observe_agent(agent, snapshot: MarketSnapshot) -> AgentObservation:
        observe = getattr(agent, "observe", None)
        if observe is not None:
            return observe(
                snapshot.symbol,
                {"snapshot": snapshot, "price": snapshot.price, "candles": snapshot.candles},
            )
        analyze = getattr(agent, "analyze", None)
        if analyze is not None:
            return analyze(snapshot)
        raise TypeError(f"Agent {agent!r} must implement observe() or analyze()")

    @staticmethod
    def _signals_from_intelligence(snapshot, intelligence):
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
