"""
Backtest Engine

Tests strategy hypotheses and Decision Engine evidence against
historical OHLCV data.

This engine does NOT place real trades. All simulation is dry-run / paper.
"""

from __future__ import annotations

from atlas.decision.engine import DecisionEngine
from atlas.models.action import Action
from atlas.models.analysis_result import AnalysisResult
from atlas.trading.backtest_result import BacktestResult
from atlas.trading.historical_market_data import HistoricalMarketData, OHLCVBar
from atlas.trading.strategy_hypothesis import StrategyHypothesis


class BacktestEngine:
    """Runs historical backtests without live execution."""

    MA_FAST = 20
    MA_SLOW = 50
    MIN_BARS = 50

    def __init__(self, decision_engine: DecisionEngine | None = None):
        self.decision_engine = decision_engine or DecisionEngine()

    def run(
        self,
        strategy: StrategyHypothesis,
        candles: list[dict],
    ) -> BacktestResult:
        """Run a simple RSI / MA hypothesis backtest (legacy path)."""

        if not candles:
            return self._empty_result(strategy.name, strategy.symbol)

        trades: list[float] = []
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

        return self._result_from_trades(
            strategy_name=strategy.name,
            symbol=strategy.symbol,
            trades=trades,
        )

    def run_decision(
        self,
        data: HistoricalMarketData,
        *,
        strategy_name: str = "Decision Engine",
    ) -> BacktestResult:
        """Walk historical bars through DecisionEngine (dry-run only).

        Technical evidence is derived from rolling MA20/MA50 on closed
        bars. The canonical DecisionEngine owns the final BUY/SELL/HOLD.
        """

        bars = list(data.bars)
        if len(bars) < self.MIN_BARS:
            return self._empty_result(strategy_name, data.symbol)

        closes = [bar.close for bar in bars]
        trades: list[float] = []
        position: dict[str, float] | None = None

        for index in range(self.MIN_BARS - 1, len(bars)):
            window = closes[: index + 1]
            bar = bars[index]
            analysis = self._technical_analysis(
                symbol=data.symbol,
                closes=window,
            )

            decision = self.decision_engine.evaluate([analysis])
            action = decision.action
            price = bar.close

            if position is None:
                if action is Action.BUY:
                    position = {"entry": price}
                continue

            # Long-only simulation: SELL closes the position.
            if action is Action.SELL:
                trades.append(
                    (price - position["entry"]) / position["entry"]
                )
                position = None

        # Force-close any open position on the last bar (research only).
        if position is not None and bars:
            last = bars[-1].close
            trades.append(
                (last - position["entry"]) / position["entry"]
            )

        return self._result_from_trades(
            strategy_name=strategy_name,
            symbol=data.symbol,
            trades=trades,
        )

    def run_symbol(
        self,
        symbol: str,
        data: HistoricalMarketData,
    ) -> BacktestResult:
        """Convenience wrapper for decision backtests on one symbol."""

        return self.run_decision(
            data,
            strategy_name="Decision Engine",
        )

    def _technical_analysis(
        self,
        *,
        symbol: str,
        closes: list[float],
    ) -> AnalysisResult:
        """Build a single technical AnalysisResult from rolling closes."""

        ma_fast = sum(closes[-self.MA_FAST :]) / self.MA_FAST
        ma_slow = sum(closes[-self.MA_SLOW :]) / self.MA_SLOW
        price = closes[-1]

        if ma_fast > ma_slow and price >= ma_fast:
            action = Action.BUY
            confidence = 70.0
            evidence = 75.0
            reasoning = [
                f"MA{self.MA_FAST} above MA{self.MA_SLOW}.",
                "Price holds above the fast average.",
            ]
        elif ma_fast < ma_slow and price <= ma_fast:
            action = Action.SELL
            confidence = 70.0
            evidence = 75.0
            reasoning = [
                f"MA{self.MA_FAST} below MA{self.MA_SLOW}.",
                "Price holds below the fast average.",
            ]
        else:
            action = Action.HOLD
            confidence = 55.0
            evidence = 50.0
            reasoning = [
                "No clear MA trend alignment.",
            ]

        return AnalysisResult(
            analyst="technical:ma_trend",
            symbol=symbol,
            action=action,
            confidence=confidence,
            evidence=evidence,
            reasoning=reasoning,
            signal_confidence=confidence,
            metadata={
                "ma_fast": ma_fast,
                "ma_slow": ma_slow,
                "price": price,
            },
        )

    @staticmethod
    def _empty_result(strategy_name: str, symbol: str) -> BacktestResult:
        return BacktestResult(
            strategy_name=strategy_name,
            symbol=symbol,
            trades=0,
            wins=0,
            losses=0,
            win_rate=0.0,
            total_return=0.0,
            profit_factor=0.0,
            max_drawdown=0.0,
        )

    @staticmethod
    def _result_from_trades(
        *,
        strategy_name: str,
        symbol: str,
        trades: list[float],
    ) -> BacktestResult:

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
            trade for trade in trades if trade > 0
        )
        gross_loss = abs(
            sum(trade for trade in trades if trade < 0)
        )

        if gross_loss:
            profit_factor = gross_profit / gross_loss
        elif gross_profit:
            profit_factor = float("inf")
        else:
            profit_factor = 0.0

        equity = 1.0
        peak = 1.0
        max_drawdown = 0.0

        for trade in trades:
            equity *= 1 + trade
            peak = max(peak, equity)
            drawdown = ((peak - equity) / peak) * 100
            max_drawdown = max(max_drawdown, drawdown)

        return BacktestResult(
            strategy_name=strategy_name,
            symbol=symbol,
            trades=trade_count,
            wins=wins,
            losses=losses,
            win_rate=round(win_rate, 2),
            total_return=round(total_return, 2),
            profit_factor=(
                round(profit_factor, 2)
                if profit_factor != float("inf")
                else float("inf")
            ),
            max_drawdown=round(max_drawdown, 2),
        )
