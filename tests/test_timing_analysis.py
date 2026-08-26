from atlas.trading.strategy_hypothesis import (
    StrategyHypothesis,
)
from atlas.trading.timing_analysis import (
    TimingAnalyzer,
)


def strategy():
    return StrategyHypothesis(
        name="RSI Oversold Reversal",
        symbol="XRP-USD",
        timeframe="1h",
        entry_rule="RSI < 30",
        exit_rule="RSI > 50",
        stop_loss="2%",
        take_profit="4%",
        source="test",
    )


def test_timing_analyzer_uses_forward_windows():

    candles = [
        {
            "timestamp": "1",
            "close": 9.0,
            "high": 9.2,
            "low": 8.9,
            "rsi": 25,
        },
        {
            "timestamp": "2",
            "close": 9.2,
            "high": 9.5,
            "low": 8.95,
            "rsi": 35,
        },
        {
            "timestamp": "3",
            "close": 9.4,
            "high": 9.8,
            "low": 9.1,
            "rsi": 40,
        },
        {
            "timestamp": "4",
            "close": 9.7,
            "high": 10.0,
            "low": 9.4,
            "rsi": 45,
        },
        {
            "timestamp": "5",
            "close": 10.0,
            "high": 10.5,
            "low": 9.8,
            "rsi": 50,
        },
        {
            "timestamp": "6",
            "close": 9.8,
            "high": 10.1,
            "low": 9.6,
            "rsi": 55,
        },
    ]

    result = TimingAnalyzer().analyze(
        strategy(),
        candles,
    )

    assert result.signals == 1
    assert result.best_entry_price == 9.0
    assert result.max_favorable_excursion == 16.67
    assert result.median_favorable_excursion == 16.67
    assert result.best_window == 5
    assert result.holding_candles == 5


def test_timing_analyzer_reports_no_signal():

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
        strategy(),
        candles,
    )

    assert result.signals == 0
    assert result.max_favorable_excursion == 0.0
    assert result.max_adverse_excursion == 0.0
    assert result.best_entry_price is None
