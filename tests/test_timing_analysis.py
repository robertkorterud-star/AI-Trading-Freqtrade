from atlas.trading.strategy_hypothesis import (
    StrategyHypothesis,
)
from atlas.trading.timing_analysis import (
    TimingAnalyzer,
)


def test_timing_analyzer_finds_rsi_opportunity():

    strategy = StrategyHypothesis(
        name="RSI Oversold Reversal",
        symbol="XRP-USD",
        timeframe="1h",
        entry_rule="RSI < 30",
        exit_rule="RSI > 50",
        stop_loss="2%",
        take_profit="4%",
        source="test",
    )

    candles = [
        {
            "timestamp": "1",
            "close": 9.0,
            "high": 9.2,
            "low": 8.9,
            "rsi": 25,
            "ma20": 9.0,
            "ma50": 9.2,
        },
        {
            "timestamp": "2",
            "close": 10.0,
            "high": 10.5,
            "low": 9.5,
            "rsi": 40,
            "ma20": 9.2,
            "ma50": 9.1,
        },
        {
            "timestamp": "3",
            "close": 11.5,
            "high": 12.0,
            "low": 10.8,
            "rsi": 65,
            "ma20": 9.8,
            "ma50": 9.3,
        },
    ]

    result = TimingAnalyzer().analyze(
        strategy,
        candles,
    )

    assert result.signals == 1
    assert result.best_entry_price == 9.0
    assert result.best_exit_price == 12.0
    assert result.best_return == 33.33
    assert result.holding_candles == 2


def test_timing_analyzer_handles_no_signal():

    strategy = StrategyHypothesis(
        name="RSI Oversold Reversal",
        symbol="XRP-USD",
        timeframe="1h",
        entry_rule="RSI < 30",
        exit_rule="RSI > 50",
        stop_loss="2%",
        take_profit="4%",
        source="test",
    )

    candles = [
        {
            "timestamp": "1",
            "close": 9.0,
            "high": 9.2,
            "low": 8.9,
            "rsi": 50,
        },
        {
            "timestamp": "2",
            "close": 9.2,
            "high": 9.4,
            "low": 9.0,
            "rsi": 55,
        },
    ]

    result = TimingAnalyzer().analyze(
        strategy,
        candles,
    )

    assert result.signals == 0
    assert result.best_return == 0.0
    assert result.best_entry_price is None
