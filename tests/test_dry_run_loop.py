from datetime import datetime
from unittest.mock import Mock

from atlas.agents.base import AgentObservation
from atlas.trading.dry_run_loop import DryRunLoop
from atlas.trading.market_data import Candle, MarketSnapshot
from atlas.trading.ml_baseline import LogisticRegressionBaseline
from atlas.trading.ml_signal import MLPredictionSignal
from atlas.trading.prediction_signal_service import PredictionSignalService
from atlas.trading.prediction_training_dataset import PredictionTrainingExample


class BullishAgent:
    name = "bullish"

    def analyze(self, snapshot):
        return AgentObservation(
            agent=self.name,
            symbol=snapshot.symbol,
            score=0.90,
            confidence=0.90,
            direction="bullish",
            reason="strong bullish test signal",
        )


class BearishAgent:
    name = "bearish"

    def analyze(self, snapshot):
        return AgentObservation(
            agent=self.name,
            symbol=snapshot.symbol,
            score=-0.90,
            confidence=0.90,
            direction="bearish",
            reason="strong bearish test signal",
        )


def snapshot():
    candles = [
        Candle(
            timestamp=i,
            open=100 + (i - 1) * 0.15,
            high=101 + (i - 1) * 0.15,
            low=99 + (i - 1) * 0.15,
            close=100 + (i - 1) * 0.15,
            volume=1000 + i * 100,
        )
        for i in range(1, 23)
    ]

    candles.append(
        Candle(
            timestamp=23,
            open=103,
            high=105,
            low=102,
            close=104,
            volume=3300,
        )
    )

    return MarketSnapshot.from_candles(
        "BTC-USD",
        candles,
    )


def _model() -> LogisticRegressionBaseline:
    model = LogisticRegressionBaseline(learning_rate=0.1, epochs=1000)
    model.fit([
        PredictionTrainingExample(
            features={"trend": -1.0},
            outcome=1.0,
            symbol="BTC-USD",
            action="BUY",
            timestamp=datetime(2026, 1, 1),
        ),
        PredictionTrainingExample(
            features={"trend": 1.0},
            outcome=0.0,
            symbol="BTC-USD",
            action="BUY",
            timestamp=datetime(2026, 1, 2),
        ),
    ])
    return model


def test_dry_run_loop_connects_agents_to_execution():
    loop = DryRunLoop(
        agents=[BullishAgent()],
    )

    result = loop.process(snapshot())

    assert result.symbol == "BTC-USD"
    assert result.price == 104
    assert len(result.observations) == 1
    assert result.intelligence_score > 0
    assert result.execution.symbol == "BTC-USD"


def test_conflicting_agents_reduce_intelligence():
    loop = DryRunLoop(
        agents=[
            BullishAgent(),
            BearishAgent(),
        ],
    )

    result = loop.process(snapshot())

    assert abs(result.intelligence_score) < 0.20


def test_loop_never_uses_live_exchange():
    loop = DryRunLoop(
        agents=[BullishAgent()],
    )

    result = loop.process(snapshot())

    assert result.execution.equity > 0
    assert loop.trader.portfolio.cash > 0


def test_dry_run_loop_uses_algorithm_pipeline():
    from atlas.algorithms.pipeline import AlgorithmPipeline

    loop = DryRunLoop(
        agents=[BullishAgent()],
    )

    assert isinstance(loop.algorithm_pipeline, AlgorithmPipeline)

    result = loop.process(snapshot())

    assert len(result.algorithm_signals) == 5
    assert {
        signal.algorithm
        for signal in result.algorithm_signals
    } == {
        "intraday_momentum",
        "intraday_trend",
        "intraday_breakout",
        "intraday_mean_reversion",
        "intraday_vwap",
    }


def test_dry_run_loop_connects_algorithm_pipeline_to_orchestrator():
    from atlas.algorithms.orchestrator import DecisionOrchestrator
    from atlas.algorithms.pipeline import AlgorithmPipeline

    loop = DryRunLoop(
        agents=[BullishAgent()],
    )

    assert isinstance(loop.algorithm_pipeline, AlgorithmPipeline)
    assert isinstance(loop.orchestrator, DecisionOrchestrator)
    assert loop.orchestrator.algorithm_pipeline is loop.algorithm_pipeline

    result = loop.process(snapshot())

    assert result.algorithm_signals


def test_dry_run_loop_generates_algorithm_signals_only_once():
    loop = DryRunLoop(agents=[BullishAgent()])
    analyze = Mock(wraps=loop.algorithm_pipeline.analyze)
    loop.algorithm_pipeline.analyze = analyze

    result = loop.process(snapshot())

    assert analyze.call_count == 1
    assert result.algorithm_signals
    assert result.decision is not None


def test_dry_run_loop_passes_precomputed_signals_and_fusion_to_orchestrator():
    loop = DryRunLoop(agents=[BullishAgent()])
    decide = Mock(wraps=loop.orchestrator.decide)
    loop.orchestrator.decide = decide

    result = loop.process(snapshot())

    call = decide.call_args
    assert call is not None
    assert call.kwargs["algorithm_signals"] == list(result.algorithm_signals)
    assert call.kwargs["fusion_result"] is not None

    # The orchestrator consumes the already-generated package instead
    # of receiving market data and regenerating the algorithm signals.
    assert call.kwargs.get("market_data") is None


def test_dry_run_loop_adds_optional_ml_prediction_signal():
    service = PredictionSignalService(
        signal=MLPredictionSignal(_model()),
    )
    loop = DryRunLoop(
        agents=[BullishAgent()],
        prediction_signal_service=service,
    )

    result = loop.process(snapshot())

    assert len(result.algorithm_signals) == 6
    assert sum(
        signal.algorithm == "ml_baseline"
        for signal in result.algorithm_signals
    ) == 1
    assert all(
        signal.symbol == "BTC-USD"
        for signal in result.algorithm_signals
    )

    fused_algorithms = {
        signal.algorithm
        for signal in loop.orchestrator.last_fusion_result.signals
    }
    assert "ml_baseline" in fused_algorithms


def test_dry_run_loop_keeps_ml_prediction_optional():
    loop = DryRunLoop(agents=[BullishAgent()])

    result = loop.process(snapshot())

    assert all(
        signal.algorithm != "ml_baseline"
        for signal in result.algorithm_signals
    )


def test_process_binance_feeds_snapshot_into_dry_run():
    class FakeBinance:
        def get_klines(self, **kwargs):
            return [
                [
                    1710000000000 + i * 60000,
                    str(100 + i * 0.2),
                    str(101 + i * 0.2),
                    str(99 + i * 0.2),
                    str(100.5 + i * 0.2),
                    "10",
                ]
                for i in range(23)
            ]

    loop = DryRunLoop(agents=[BullishAgent()])

    result = loop.process_binance(
        FakeBinance(),
        symbol="BTCUSDT",
        interval="1m",
        limit=23,
    )

    assert result.symbol == "BTCUSDT"
    assert result.price == 104.9
    assert result.execution.symbol == "BTCUSDT"
    assert len(result.observations) == 1
