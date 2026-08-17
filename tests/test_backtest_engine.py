from atlas.trading.backtest_engine import BacktestEngine
from atlas.trading.strategy_hypothesis import (
    StrategyHypothesis,
)


def make_strategy():
    return StrategyHypothesis(
        name="RSI Oversold Reversal",
        symbol="NVDA",
        timeframe="15m",
        entry_rule="RSI < 30",
        exit_rule="RSI > 50",
        stop_loss="2%",
        take_profit="4%",
        source="YouTube",
    )


def test_backtest_finds_profitable_trade():

    candles = [
        {"close": 100, "rsi": 25},
        {"close": 101, "rsi": 28},
        {"close": 104, "rsi": 55},
    ]

    result = BacktestEngine().run(
        make_strategy(),
        candles,
    )

    assert result.trades == 1
    assert result.wins == 1
    assert result.losses == 0
    assert result.win_rate == 100.0
    assert result.total_return == 4.0


def test_backtest_finds_losing_trade():

    candles = [
        {"close": 100, "rsi": 25},
        {"close": 98, "rsi": 25},
    ]

    result = BacktestEngine().run(
        make_strategy(),
        candles,
    )

    assert result.trades == 1
    assert result.wins == 0
    assert result.losses == 1
    assert result.win_rate == 0.0


def test_backtest_handles_empty_data():

    result = BacktestEngine().run(
        make_strategy(),
        [],
    )

    assert result.trades == 0
    assert result.win_rate == 0.0
    assert result.total_return == 0.0


def make_ma_strategy():
    return StrategyHypothesis(
        name="Moving Average Crossover",
        symbol="NVDA",
        timeframe="1h",
        entry_rule="MA20 crosses above MA50",
        exit_rule="MA20 crosses below MA50",
        stop_loss="3%",
        take_profit="6%",
        source="Finnhub",
    )


def test_backtest_finds_ma_crossover_trade():

    candles = [
        {
            "close": 100,
            "ma20": 99,
            "ma50": 100,
        },
        {
            "close": 102,
            "ma20": 101,
            "ma50": 100,
        },
        {
            "close": 105,
            "ma20": 104,
            "ma50": 101,
        },
        {
            "close": 104,
            "ma20": 100,
            "ma50": 102,
        },
    ]

    result = BacktestEngine().run(
        make_ma_strategy(),
        candles,
    )

    assert result.trades == 1
    assert result.wins == 1
    assert result.losses == 0
    assert result.win_rate == 100.0
