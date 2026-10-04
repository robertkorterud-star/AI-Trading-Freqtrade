from datetime import datetime, timedelta, timezone

from atlas.trading.backtest_engine import BacktestEngine
from atlas.trading.historical_market_data import (
    HistoricalMarketData,
    OHLCVBar,
)


def _historical_data(bar_count: int = 60) -> HistoricalMarketData:
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    bars = []

    for index in range(bar_count):
        price = 100.0 + index
        bars.append(
            OHLCVBar(
                timestamp=start + timedelta(hours=4 * index),
                open=price,
                high=price + 1.0,
                low=price - 1.0,
                close=price + 0.5,
                volume=1000.0 + index,
            )
        )

    return HistoricalMarketData(
        symbol="BTC-USD",
        bars=bars,
        timeframe="4h",
        source="test",
    )


def test_historical_snapshots_never_include_future_bars():
    data = _historical_data()

    snapshots = list(
        BacktestEngine().historical_snapshots(
            data,
            warmup_bars=50,
        )
    )

    assert len(snapshots) == 11

    for offset, snapshot in enumerate(snapshots):
        current_index = 49 + offset
        expected_bars = data.bars[: current_index + 1]

        assert snapshot.symbol == data.symbol
        assert len(snapshot.candles) == current_index + 1
        assert snapshot.price == expected_bars[-1].close
        assert snapshot.timestamp == expected_bars[-1].timestamp.timestamp()

        assert tuple(
            candle.timestamp
            for candle in snapshot.candles
        ) == tuple(
            bar.timestamp.timestamp()
            for bar in expected_bars
        )

        assert all(
            candle.timestamp <= snapshot.timestamp
            for candle in snapshot.candles
        )


class RecordingReplayLoop:
    def __init__(self):
        self.snapshots = []

    def process(self, snapshot):
        self.snapshots.append(snapshot)
        return object()


def test_historical_replay_delegates_snapshots_to_modern_loop():
    data = _historical_data()
    loop = RecordingReplayLoop()

    results = BacktestEngine().replay(
        data,
        loop=loop,
        warmup_bars=50,
    )

    assert len(results) == 11
    assert len(loop.snapshots) == 11

    for snapshot, result_bar in zip(
        loop.snapshots,
        data.bars[49:],
    ):
        assert snapshot.symbol == data.symbol
        assert snapshot.timestamp == result_bar.timestamp.timestamp()
        assert snapshot.price == result_bar.close

    assert len(loop.snapshots[0].candles) == 50
    assert len(loop.snapshots[-1].candles) == 60


def test_historical_replay_runs_through_real_dry_run_loop():
    from atlas.trading.dry_run_loop import DryRunLoop

    data = _historical_data()
    loop = DryRunLoop(agents=[])

    results = BacktestEngine().replay(
        data,
        loop=loop,
        warmup_bars=50,
    )

    assert len(results) == 11

    for result, bar in zip(results, data.bars[49:]):
        assert result.symbol == data.symbol
        assert result.price == bar.close
        assert result.canonical_decision is not None
        assert result.execution is not None

    engine = loop.orchestrator.decision_engine

    assert engine.risk_manager is loop.risk_manager
    assert engine.portfolio_manager is loop.portfolio_manager
    assert engine.last_risk_assessment is not None
    assert engine.last_portfolio_assessment is not None


def test_multi_symbol_replay_is_globally_chronological():
    """Multiple symbols must share one chronological modern replay stream."""
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)

    btc = _historical_data(bar_count=52)

    eth_bars = []
    for index in range(52):
        price = 2000.0 + index
        eth_bars.append(
            OHLCVBar(
                timestamp=start + timedelta(hours=4 * index, minutes=30),
                open=price,
                high=price + 1.0,
                low=price - 1.0,
                close=price + 0.5,
                volume=2000.0 + index,
            )
        )

    eth = HistoricalMarketData(
        symbol="ETH-USD",
        bars=eth_bars,
        timeframe="4h",
        source="test",
    )

    loop = RecordingReplayLoop()

    results = BacktestEngine().replay_many(
        [btc, eth],
        loop=loop,
        warmup_bars=50,
    )

    assert len(results) == 6
    assert [snapshot.symbol for snapshot in loop.snapshots] == [
        "BTC-USD",
        "ETH-USD",
        "BTC-USD",
        "ETH-USD",
        "BTC-USD",
        "ETH-USD",
    ]
    assert [snapshot.timestamp for snapshot in loop.snapshots] == sorted(
        snapshot.timestamp for snapshot in loop.snapshots
    )

    assert len(loop.snapshots[0].candles) == 50
    assert len(loop.snapshots[1].candles) == 50
    assert len(loop.snapshots[-2].candles) == 52
    assert len(loop.snapshots[-1].candles) == 52


def test_multi_symbol_replay_runs_through_shared_real_dry_run_loop():
    """Multiple symbols must share one canonical runtime and portfolio context."""
    from atlas.trading.dry_run_loop import DryRunLoop

    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    btc = _historical_data(bar_count=52)

    eth_bars = []
    for index in range(52):
        price = 2000.0 + index
        eth_bars.append(
            OHLCVBar(
                timestamp=start + timedelta(hours=4 * index, minutes=30),
                open=price,
                high=price + 1.0,
                low=price - 1.0,
                close=price + 0.5,
                volume=2000.0 + index,
            )
        )

    eth = HistoricalMarketData(
        symbol="ETH-USD",
        bars=eth_bars,
        timeframe="4h",
        source="test",
    )

    loop = DryRunLoop(agents=[])

    results = BacktestEngine().replay_many(
        [btc, eth],
        loop=loop,
        warmup_bars=50,
    )

    assert len(results) == 6
    assert [result.symbol for result in results] == [
        "BTC-USD",
        "ETH-USD",
        "BTC-USD",
        "ETH-USD",
        "BTC-USD",
        "ETH-USD",
    ]

    assert all(
        result.canonical_decision is not None
        for result in results
    )
    assert all(
        result.execution is not None
        for result in results
    )

    engine = loop.orchestrator.decision_engine

    assert engine.risk_manager is loop.risk_manager
    assert engine.portfolio_manager is loop.portfolio_manager

    assert "BTC-USD" in loop._latest_prices
    assert "ETH-USD" in loop._latest_prices
    assert loop._latest_prices["BTC-USD"] == btc.bars[-1].close
    assert loop._latest_prices["ETH-USD"] == eth.bars[-1].close


def test_multi_symbol_replay_carries_executed_exposure_into_next_symbol_decision():
    """An executed trade must affect portfolio context for the next symbol."""
    from atlas.models.action import Action
    from atlas.risk.manager import RiskAssessment
    from atlas.trading.dry_run_loop import DryRunLoop

    start = datetime(2026, 1, 1, tzinfo=timezone.utc)

    btc = _historical_data(bar_count=50)

    eth_bars = []
    for index in range(50):
        price = 2000.0 + index
        eth_bars.append(
            OHLCVBar(
                timestamp=start + timedelta(hours=4 * index, minutes=30),
                open=price,
                high=price + 1.0,
                low=price - 1.0,
                close=price + 0.5,
                volume=2000.0 + index,
            )
        )

    eth = HistoricalMarketData(
        symbol="ETH-USD",
        bars=eth_bars,
        timeframe="4h",
        source="test",
    )

    loop = DryRunLoop(agents=[])

    original_decide = loop.orchestrator.decide
    captured = []

    def capturing_decide(*args, **kwargs):
        captured.append(
            {
                "symbol": args[0],
                "equity": kwargs["equity"],
                "current_exposure_pct": kwargs["current_exposure_pct"],
                "portfolio_positions": tuple(kwargs["portfolio_positions"]),
            }
        )

        result = original_decide(*args, **kwargs)

        if args[0] == "BTC-USD":
            decision = result.canonical_decision
            approved_quantity = 10.0

            object.__setattr__(decision, "action", Action.BUY)
            object.__setattr__(
                decision,
                "risk_assessment",
                RiskAssessment(
                    action=Action.BUY,
                    allowed=True,
                    risk_level="LOW",
                    position_size=approved_quantity,
                    position_value=approved_quantity * kwargs["price"],
                    stop_loss_price=None,
                    take_profit_price=None,
                    reasons=("Approved BTC size for replay contract test.",),
                ),
            )
            object.__setattr__(result.decision, "action", Action.BUY)

        return result

    loop.orchestrator.decide = capturing_decide

    results = BacktestEngine().replay_many(
        [btc, eth],
        loop=loop,
        warmup_bars=50,
    )

    assert len(results) == 2
    assert captured[0]["symbol"] == "BTC-USD"
    assert captured[1]["symbol"] == "ETH-USD"

    assert results[0].execution.quantity == 10.0
    assert "BTC-USD" in loop.trader.portfolio.positions

    btc_position = loop.trader.portfolio.positions["BTC-USD"]
    expected_btc_value = btc_position.quantity * btc.bars[-1].close

    eth_context = captured[1]

    assert eth_context["current_exposure_pct"] > 0.0
    assert any(
        position.symbol == "BTC-USD"
        and position.market_value == expected_btc_value
        for position in eth_context["portfolio_positions"]
    )
