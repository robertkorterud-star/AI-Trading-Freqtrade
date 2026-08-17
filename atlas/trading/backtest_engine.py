"""
Backtest Engine

Tests strategy hypotheses against historical OHLC data.

This engine does NOT place trades.
"""

from atlas.trading.backtest_result import BacktestResult
from atlas.trading.strategy_hypothesis import StrategyHypothesis


class BacktestEngine:
    """Runs historical backtests."""

    def run(
        self,
        strategy: StrategyHypothesis,
        candles: list[dict],
    ) -> BacktestResult:
        """Run a simple RSI oversold backtest."""

        if not candles:
            return BacktestResult(
                strategy_name=strategy.name,
                symbol=strategy.symbol,
                trades=0,
                wins=0,
                losses=0,
                win_rate=0.0,
                total_return=0.0,
                profit_factor=0.0,
                max_drawdown=0.0,
            )

        trades = []
        position = None
        previous_ma20 = None
        previous_ma50 = None

        for candle in candles:

            close = float(candle["close"])
            rsi = float(candle.get("rsi", 50.0))

            ma20 = candle.get("ma20")
            ma50 = candle.get("ma50")

            if ma20 is not None:
                ma20 = float(ma20)

            if ma50 is not None:
                ma50 = float(ma50)

            if position is None:

                if (
                    strategy.name
                    == "RSI Oversold Reversal"
                    and rsi < 30
                ):
                    position = {
                        "entry": close,
                        "stop": close * 0.98,
                        "target": close * 1.04,
                    }

                elif (
                    strategy.name
                    == "Moving Average Crossover"
                    and previous_ma20 is not None
                    and previous_ma50 is not None
                    and ma20 is not None
                    and ma50 is not None
                    and previous_ma20 <= previous_ma50
                    and ma20 > ma50
                ):
                    position = {
                        "entry": close,
                        "stop": close * 0.97,
                        "target": close * 1.06,
                    }

                previous_ma20 = ma20
                previous_ma50 = ma50
                continue

            if close <= position["stop"]:

                trades.append(
                    (close - position["entry"])
                    / position["entry"]
                )

                position = None

            elif close >= position["target"]:

                trades.append(
                    (close - position["entry"])
                    / position["entry"]
                )

                position = None

            elif (
                strategy.name
                == "RSI Oversold Reversal"
                and rsi > 50
            ):

                trades.append(
                    (close - position["entry"])
                    / position["entry"]
                )

                position = None

            elif (
                strategy.name
                == "Moving Average Crossover"
                and previous_ma20 is not None
                and previous_ma50 is not None
                and ma20 is not None
                and ma50 is not None
                and previous_ma20 >= previous_ma50
                and ma20 < ma50
            ):

                trades.append(
                    (close - position["entry"])
                    / position["entry"]
                )

                position = None

            previous_ma20 = ma20
            previous_ma50 = ma50

        wins = sum(1 for trade in trades if trade > 0)
        losses = sum(1 for trade in trades if trade <= 0)

        trade_count = len(trades)

        win_rate = (
            (wins / trade_count) * 100
            if trade_count
            else 0.0
        )

        total_return = sum(trades) * 100

        gross_profit = sum(
            trade
            for trade in trades
            if trade > 0
        )

        gross_loss = abs(
            sum(
                trade
                for trade in trades
                if trade < 0
            )
        )

        profit_factor = (
            gross_profit / gross_loss
            if gross_loss
            else (
                float("inf")
                if gross_profit
                else 0.0
            )
        )

        equity = 1.0
        peak = 1.0
        max_drawdown = 0.0

        for trade in trades:

            equity *= 1 + trade
            peak = max(peak, equity)

            drawdown = (
                (peak - equity) / peak
            ) * 100

            max_drawdown = max(
                max_drawdown,
                drawdown,
            )

        return BacktestResult(
            strategy_name=strategy.name,
            symbol=strategy.symbol,
            trades=trade_count,
            wins=wins,
            losses=losses,
            win_rate=round(win_rate, 2),
            total_return=round(
                total_return,
                2,
            ),
            profit_factor=round(
                profit_factor,
                2,
            )
            if profit_factor != float("inf")
            else float("inf"),
            max_drawdown=round(
                max_drawdown,
                2,
            ),
        )
