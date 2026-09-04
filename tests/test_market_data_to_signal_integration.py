from atlas.adapters.binance_market_data import BinanceMarketData
from atlas.algorithms.base import AlgorithmSignal
from atlas.algorithms.fusion import SignalFusion
from atlas.algorithms.pipeline import AlgorithmPipeline
from atlas.algorithms.registry import AlgorithmRegistry
from atlas.models.action import Action
from atlas.trading.market_data import Candle, MarketSnapshot


class FakeBinanceAdapter:
    """Deterministic Binance adapter for the integration contract."""

    def get_klines(self, symbol, interval="1m", limit=100):
        return [
            [
                1_700_000_000_000,
                "100.0",
                "101.0",
                "99.0",
                "100.5",
                "10.0",
            ],
            [
                1_700_000_060_000,
                "100.5",
                "102.0",
                "100.0",
                "101.5",
                "12.0",
            ],
            [
                1_700_000_120_000,
                "101.5",
                "103.0",
                "101.0",
                "102.5",
                "14.0",
            ],
        ]


class RecordingAlgorithm:
    """Minimal algorithm proving normalized candles reach the signal layer."""

    name = "recording"
    timeframe = "1m"

    def __init__(self):
        self.calls = []

    def generate_signal(self, symbol, candles):
        self.calls.append((symbol, candles))

        assert symbol == "BTCUSDT"
        assert isinstance(candles, list)
        assert candles
        assert all(isinstance(candle, Candle) for candle in candles)

        return AlgorithmSignal(
            algorithm=self.name,
            symbol=symbol,
            timeframe=self.timeframe,
            action=Action.BUY,
            score=100.0,
            confidence=80.0,
            reasoning=["Normalized market data reached the algorithm."],
        )


def test_binance_market_data_produces_normalized_snapshot():
    market_data = BinanceMarketData(FakeBinanceAdapter())

    snapshot = market_data.snapshot(
        symbol="BTCUSDT",
        interval="1m",
        limit=3,
    )

    assert isinstance(snapshot, MarketSnapshot)
    assert snapshot.symbol == "BTCUSDT"
    assert snapshot.price == 102.5
    assert len(snapshot.candles) == 3

    latest = snapshot.candles[-1]

    assert latest.open == 101.5
    assert latest.high == 103.0
    assert latest.low == 101.0
    assert latest.close == 102.5
    assert latest.volume == 14.0


def test_market_snapshot_can_feed_algorithm_pipeline_without_exchange_coupling():
    algorithm = RecordingAlgorithm()

    registry = AlgorithmRegistry()
    registry.register(algorithm)

    pipeline = AlgorithmPipeline(
        registry=registry,
        fusion=SignalFusion(),
    )

    snapshot = BinanceMarketData(FakeBinanceAdapter()).snapshot(
        symbol="BTCUSDT",
        interval="1m",
        limit=3,
    )

    fused, signals = pipeline.analyze(
        snapshot.symbol,
        {
            "candles": list(snapshot.candles),
        },
    )

    assert len(algorithm.calls) == 1
    assert len(signals) == 1

    assert signals[0].symbol == "BTCUSDT"
    assert signals[0].action is Action.BUY

    assert fused is not None
    assert fused.symbol == "BTCUSDT"
    assert fused.action is Action.BUY
