from datetime import datetime
from unittest.mock import Mock

import pytest

from atlas.agents.base import AgentObservation
from atlas.market.asset_type import AssetType
from atlas.trading.dry_run_loop import DryRunLoop
from atlas.trading.market_data import Candle, MarketSnapshot
from atlas.trading.ml_baseline import LogisticRegressionBaseline
from atlas.trading.ml_signal import MLPredictionSignal
from atlas.trading.multi_timeframe_analysis import MultiTimeframeAnalyzer
from atlas.trading.prediction_signal_service import PredictionSignalService
from atlas.trading.prediction_training_dataset import PredictionTrainingExample
from atlas.trading.signal_evidence import SignalEvidenceAnalyzer


class BullishAgent:
    name = "bullish"

    def analyze(self, snapshot):
        return AgentObservation(agent=self.name, symbol=snapshot.symbol, score=0.90, confidence=0.90, direction="bullish", reason="strong bullish test signal")


class BearishAgent:
    name = "bearish"

    def analyze(self, snapshot):
        return AgentObservation(agent=self.name, symbol=snapshot.symbol, score=-0.90, confidence=0.90, direction="bearish", reason="strong bearish test signal")


def snapshot():
    candles = [Candle(timestamp=i, open=100 + (i - 1) * 0.15, high=101 + (i - 1) * 0.15, low=99 + (i - 1) * 0.15, close=100 + (i - 1) * 0.15, volume=1000 + i * 100) for i in range(1, 23)]
    candles.append(Candle(timestamp=23, open=103, high=105, low=102, close=104, volume=3300))
    return MarketSnapshot.from_candles("BTC-USD", candles)


def _model() -> LogisticRegressionBaseline:
    model = LogisticRegressionBaseline(learning_rate=0.1, epochs=1000)
    model.fit([
        PredictionTrainingExample(features={"trend": -1.0}, outcome=1.0, symbol="BTC-USD", action="BUY", timestamp=datetime(2026, 1, 1)),
        PredictionTrainingExample(features={"trend": 1.0}, outcome=0.0, symbol="BTC-USD", action="BUY", timestamp=datetime(2026, 1, 2)),
    ])
    return model


def test_dry_run_loop_connects_agents_to_execution():
    loop = DryRunLoop(agents=[BullishAgent()])
    result = loop.process(snapshot())
    assert result.symbol == "BTC-USD"
    assert result.price == 104
    assert len(result.observations) == 1
    assert result.intelligence_score > 0
    assert result.execution.symbol == "BTC-USD"


def test_conflicting_agents_reduce_intelligence():
    result = DryRunLoop(agents=[BullishAgent(), BearishAgent()]).process(snapshot())
    assert abs(result.intelligence_score) < 0.20


def test_loop_never_uses_live_exchange():
    loop = DryRunLoop(agents=[BullishAgent()])
    result = loop.process(snapshot())
    assert result.execution.equity > 0
    assert loop.trader.portfolio.cash > 0


def test_dry_run_loop_uses_algorithm_pipeline():
    from atlas.algorithms.pipeline import AlgorithmPipeline
    loop = DryRunLoop(agents=[BullishAgent()])
    assert isinstance(loop.algorithm_pipeline, AlgorithmPipeline)
    result = loop.process(snapshot())
    assert len(result.algorithm_signals) == 5
    assert {signal.algorithm for signal in result.algorithm_signals} == {"intraday_momentum", "intraday_trend", "intraday_breakout", "intraday_mean_reversion", "intraday_vwap"}


def test_dry_run_loop_connects_algorithm_pipeline_to_orchestrator():
    from atlas.algorithms.orchestrator import DecisionOrchestrator
    from atlas.algorithms.pipeline import AlgorithmPipeline
    loop = DryRunLoop(agents=[BullishAgent()])
    assert isinstance(loop.algorithm_pipeline, AlgorithmPipeline)
    assert isinstance(loop.orchestrator, DecisionOrchestrator)
    assert loop.orchestrator.algorithm_pipeline is loop.algorithm_pipeline
    assert loop.process(snapshot()).algorithm_signals


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
    assert decide.call_args is not None
    assert decide.call_args.kwargs["algorithm_signals"] == list(result.algorithm_signals)
    assert decide.call_args.kwargs["fusion_result"] is not None
    assert decide.call_args.kwargs.get("market_data") is None


def test_dry_run_loop_does_not_double_count_agent_intelligence():
    """Agent observations must reach DecisionEngine only through agent:* signals."""
    loop = DryRunLoop(agents=[BullishAgent()])
    decide = Mock(wraps=loop.orchestrator.decide)
    loop.orchestrator.decide = decide

    result = loop.process(snapshot())

    assert result.observations
    assert decide.call_args is not None

    positional_signals = decide.call_args.args[1]

    assert not any(
        signal.algorithm == "market_intelligence"
        for signal in positional_signals
    )
    assert decide.call_args.kwargs["observations"] == list(result.observations)


def test_dry_run_loop_adds_optional_ml_prediction_signal():
    service = PredictionSignalService(signal=MLPredictionSignal(_model()))
    loop = DryRunLoop(agents=[BullishAgent()], prediction_signal_service=service)
    decide = Mock(wraps=loop.orchestrator.decide)
    loop.orchestrator.decide = decide
    result = loop.process(snapshot())
    assert len(result.algorithm_signals) == 6
    assert sum(signal.algorithm == "ml_baseline" for signal in result.algorithm_signals) == 1
    assert all(signal.symbol == "BTC-USD" for signal in result.algorithm_signals)
    assert "ml_baseline" in {signal.algorithm for signal in decide.call_args.kwargs["fusion_result"].signals}


def test_dry_run_loop_keeps_ml_prediction_optional():
    result = DryRunLoop(agents=[BullishAgent()]).process(snapshot())
    assert all(signal.algorithm != "ml_baseline" for signal in result.algorithm_signals)


def test_dry_run_loop_feeds_snapshot_multi_timeframe_candles_to_ml():
    base = snapshot()
    mtf = {timeframe: base.candles for timeframe in ("4h", "1h", "15m", "5m", "1m")}
    enriched = MarketSnapshot.from_candles(base.symbol, base.candles, timeframe_candles=mtf)
    service = PredictionSignalService(signal=MLPredictionSignal(_model()))
    analyzer = Mock(wraps=MultiTimeframeAnalyzer())
    loop = DryRunLoop(agents=[BullishAgent()], prediction_signal_service=service, multi_timeframe_analyzer=analyzer)
    loop.process(enriched)
    data = analyzer.analyze.call_args.args[1]
    assert set(data) == {"4h", "1h", "15m", "5m", "1m"}
    assert all("trend" in value and "momentum" in value for value in data.values())


def test_process_binance_feeds_snapshot_into_dry_run():
    class FakeBinance:
        def get_klines(self, **kwargs):
            return [[1710000000000 + i * 60000, str(100 + i * 0.2), str(101 + i * 0.2), str(99 + i * 0.2), str(100.5 + i * 0.2), "10"] for i in range(23)]
    result = DryRunLoop(agents=[BullishAgent()]).process_binance(FakeBinance(), symbol="BTCUSDT", interval="1m", limit=23)
    assert result.symbol == "BTCUSDT"
    assert result.price == 104.9
    assert result.execution.symbol == "BTCUSDT"
    assert len(result.observations) == 1


def test_dry_run_loop_uses_canonical_risk_and_portfolio_managers():
    loop = DryRunLoop(agents=[BullishAgent()])
    result = loop.process(snapshot())

    engine = loop.orchestrator.decision_engine
    assert engine.risk_manager is loop.risk_manager
    assert engine.portfolio_manager is loop.portfolio_manager
    assert engine.last_risk_assessment is not None
    assert engine.last_portfolio_assessment is not None
    assert result.execution.equity > 0


def test_process_binance_uses_trading_horizon_timeframes():
    from atlas.market.trading_horizon import TradingHorizon

    class FakeBinance:
        def __init__(self):
            self.calls = []

        def get_klines(self, **kwargs):
            self.calls.append(kwargs)
            return [
                [
                    1710000000000 + i * 60000,
                    str(100 + i * 0.2),
                    str(101 + i * 0.2),
                    str(99 + i * 0.2),
                    str(100.5 + i * 0.2),
                    "10",
                ]
                for i in range(30)
            ]

    adapter = FakeBinance()

    DryRunLoop(agents=[BullishAgent()]).process_binance(
        adapter,
        symbol="BTCUSDT",
        horizon=TradingHorizon.DAY_TRADE,
        limit=30,
    )

    assert [call["interval"] for call in adapter.calls] == [
        "1h",
        "15m",
        "5m",
    ]


def test_process_binance_passes_crypto_freshness_into_prediction_evidence(monkeypatch):
    from atlas.market.market_context import MarketContextService

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
                for i in range(250)
            ]

    service = PredictionSignalService(signal=MLPredictionSignal(_model()))
    analyzer = Mock(wraps=SignalEvidenceAnalyzer())
    loop = DryRunLoop(
        agents=[BullishAgent()],
        prediction_signal_service=service,
        signal_evidence_analyzer=analyzer,
    )

    monkeypatch.setattr(
        MarketContextService,
        "data_freshness",
        Mock(return_value="STALE"),
    )

    loop.process_binance(
        FakeBinance(),
        symbol="BTCUSDT",
        interval="1m",
        limit=250,
    )

    prediction_call = next(
        call
        for call in analyzer.analyze.call_args_list
        if call.kwargs.get("data_freshness") is not None
    )

    assert prediction_call.kwargs["data_freshness"] == "STALE"
    MarketContextService.data_freshness.assert_called_once_with(
        asset_type=AssetType.CRYPTO,
        now_timestamp=pytest.approx(1710014940.0),
        latest_candle_timestamp=pytest.approx(1710014940.0),
        expected_interval_seconds=60.0,
    )


def test_dry_run_loop_forwards_open_position_to_orchestrator():
    """Dry-run canonical decision must see the actual symbol position."""
    from atlas.trading.dry_run_loop import DryRunLoop

    loop = DryRunLoop(agents=[])

    loop.trader.portfolio.buy(
        "BTC-USD",
        price=100.0,
        quantity=2.5,
    )

    captured = {}
    original_decide = loop.orchestrator.decide

    def capturing_decide(*args, **kwargs):
        captured["current_position"] = kwargs.get("current_position")
        captured["last_buy_price"] = kwargs.get("last_buy_price")
        captured["average_price"] = kwargs.get("average_price")
        captured["peak_price"] = kwargs.get("peak_price")
        return original_decide(*args, **kwargs)

    loop.orchestrator.decide = capturing_decide

    loop.process(snapshot())

    assert captured["current_position"] == 2.5
    assert captured["average_price"] == 100.0


def test_dry_run_loop_executes_canonical_risk_approved_quantity():
    """DryRunLoop must not replace canonical RiskManager sizing at execution."""
    from atlas.models.action import Action
    from atlas.risk.manager import RiskAssessment

    loop = DryRunLoop(agents=[])

    approved_quantity = 1.25
    captured = {}

    original_decide = loop.orchestrator.decide

    def canonical_sized_decide(*args, **kwargs):
        result = original_decide(*args, **kwargs)
        decision = result.canonical_decision

        object.__setattr__(decision, "action", Action.BUY)
        object.__setattr__(
            decision,
            "risk_assessment",
            RiskAssessment(
                action=Action.BUY,
                allowed=True,
                risk_level="LOW",
                position_size=approved_quantity,
                position_value=approved_quantity * 100.0,
                stop_loss_price=None,
                take_profit_price=None,
                reasons=("Approved canonical size for regression test.",),
            ),
        )
        return result

    loop.orchestrator.decide = canonical_sized_decide

    original_process_signal = loop.trader.process_signal

    def capture_execution(*args, **kwargs):
        result = original_process_signal(*args, **kwargs)
        captured["quantity"] = result.quantity
        return result

    loop.trader.process_signal = capture_execution

    loop.process(snapshot())

    assert captured["quantity"] == approved_quantity

def test_portfolio_context_uses_last_observed_price_per_symbol():
    """A snapshot for one symbol must not reprice every open position."""
    from atlas.trading.dry_run_loop import DryRunLoop
    from atlas.trading.market_data import MarketSnapshot

    loop = DryRunLoop(agents=[])

    # Existing ETH position bought at 1,500.
    loop.trader.portfolio.buy(
        "ETH-USD",
        price=1500.0,
        quantity=2.0,
    )

    # First observe ETH trading at 2,000.
    eth = MarketSnapshot(
        symbol="ETH-USD",
        price=2000.0,
        timestamp=1.0,
        candles=(),
    )
    loop._portfolio_context(eth)

    # Then process an unrelated BTC price.
    btc = MarketSnapshot(
        symbol="BTC-USD",
        price=100.0,
        timestamp=2.0,
        candles=(),
    )
    equity, exposure_pct, _, positions = loop._portfolio_context(btc)

    eth_position = next(
        position for position in positions
        if position.symbol == "ETH-USD"
    )

    # ETH must retain its last observed ETH price: 2 * 2,000 = 4,000.
    assert eth_position.market_value == 4000.0

    # Cash after ETH purchase is 97,000; marked ETH value is 4,000.
    # fee_rate default is 0.001, so account for the 3.0 entry fee.
    assert equity == 100997.0
