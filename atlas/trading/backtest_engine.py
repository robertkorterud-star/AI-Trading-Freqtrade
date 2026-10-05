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
from atlas.trading.market_data import Candle, MarketSnapshot
from atlas.trading.strategy_hypothesis import StrategyHypothesis


class BacktestEngine:
    """Runs historical backtests without live execution."""

    MA_FAST = 20
    MA_SLOW = 50
    MOMENTUM_LOOKBACK = 10
    VOLUME_LOOKBACK = 20
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

    def historical_snapshots(
        self,
        data: HistoricalMarketData,
        *,
        warmup_bars: int = MIN_BARS,
        timeframe_data: dict[str, HistoricalMarketData] | None = None,
    ):
        """Yield chronological MarketSnapshots without future bars."""

        if warmup_bars <= 0:
            raise ValueError("warmup_bars must be greater than zero")

        bars = data.bars
        if len(bars) < warmup_bars:
            return

        candles = tuple(
            Candle(
                timestamp=bar.timestamp.timestamp(),
                open=bar.open,
                high=bar.high,
                low=bar.low,
                close=bar.close,
                volume=bar.volume,
            )
            for bar in bars
        )

        normalized_timeframes = {
            timeframe: tuple(
                Candle(
                    timestamp=bar.timestamp.timestamp(),
                    open=bar.open,
                    high=bar.high,
                    low=bar.low,
                    close=bar.close,
                    volume=bar.volume,
                )
                for bar in timeframe_history.bars
            )
            for timeframe, timeframe_history in (timeframe_data or {}).items()
        }

        for end_index in range(warmup_bars - 1, len(candles)):
            current_bar = bars[end_index]
            available_at = (
                current_bar.timestamp.timestamp()
                + self._timeframe_seconds(data.timeframe)
            )

            closed_timeframes = {
                timeframe: tuple(
                    candle
                    for candle in timeframe_candles
                    if (
                        candle.timestamp
                        + self._timeframe_seconds(timeframe)
                        <= available_at
                    )
                )
                for timeframe, timeframe_candles in normalized_timeframes.items()
            }

            yield MarketSnapshot.from_candles(
                data.symbol,
                candles[: end_index + 1],
                timeframe=data.timeframe,
                timeframe_candles=closed_timeframes,
            )

    @staticmethod
    def _timeframe_seconds(timeframe: str) -> float:
        """Convert historical timeframe notation to seconds."""
        unit_seconds = {
            "m": 60.0,
            "h": 3600.0,
            "d": 86400.0,
            "w": 604800.0,
        }
        try:
            return float(timeframe[:-1]) * unit_seconds[timeframe[-1]]
        except (KeyError, ValueError):
            raise ValueError(
                f"Unsupported historical timeframe: {timeframe}"
            ) from None

    def replay(
        self,
        data: HistoricalMarketData,
        *,
        loop,
        warmup_bars: int = MIN_BARS,
        timeframe_data: dict[str, HistoricalMarketData] | None = None,
    ) -> list[object]:
        """Replay historical snapshots through an existing ATLAS loop."""

        return [
            loop.process(snapshot)
            for snapshot in self.historical_snapshots(
                data,
                warmup_bars=warmup_bars,
                timeframe_data=timeframe_data,
            )
        ]

    def replay_many(
        self,
        datasets: list[HistoricalMarketData],
        *,
        loop,
        warmup_bars: int = MIN_BARS,
    ) -> list[object]:
        """Replay multiple symbols through one chronological ATLAS loop."""

        snapshots = [
            snapshot
            for data in datasets
            for snapshot in self.historical_snapshots(
                data,
                warmup_bars=warmup_bars,
            )
        ]
        snapshots.sort(key=lambda snapshot: snapshot.timestamp)

        return [
            loop.process(snapshot)
            for snapshot in snapshots
        ]

    def run_decision(
        self,
        data: HistoricalMarketData,
        *,
        strategy_name: str = "Decision Engine",
    ) -> BacktestResult:
        """Walk historical bars through DecisionEngine (dry-run only).

        Each bar produces multi-signal evidence (trend, momentum, volume)
        that is passed to the canonical DecisionEngine. No live orders.
        """

        bars = list(data.bars)
        if len(bars) < self.MIN_BARS:
            return self._empty_result(strategy_name, data.symbol)

        closes = [bar.close for bar in bars]
        volumes = [bar.volume for bar in bars]
        trades: list[float] = []
        position: dict[str, float] | None = None

        for index in range(self.MIN_BARS - 1, len(bars)):
            close_window = closes[: index + 1]
            volume_window = volumes[: index + 1]
            bar = bars[index]

            analyses = self._build_analyses(
                symbol=data.symbol,
                closes=close_window,
                volumes=volume_window,
            )

            decision = self.decision_engine.evaluate(analyses)
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

    def _build_analyses(
        self,
        *,
        symbol: str,
        closes: list[float],
        volumes: list[float],
    ) -> list[AnalysisResult]:
        """Build multi-signal AnalysisResult list for one bar."""

        return [
            self._trend_analysis(symbol=symbol, closes=closes),
            self._momentum_analysis(symbol=symbol, closes=closes),
            self._volume_analysis(
                symbol=symbol,
                closes=closes,
                volumes=volumes,
            ),
        ]

    def _trend_analysis(
        self,
        *,
        symbol: str,
        closes: list[float],
    ) -> AnalysisResult:
        """MA trend signal aligned with ATLAS technical direction rules."""

        ma_fast = sum(closes[-self.MA_FAST :]) / self.MA_FAST
        ma_slow = sum(closes[-self.MA_SLOW :]) / self.MA_SLOW
        price = closes[-1]

        if price > ma_fast > ma_slow:
            action = Action.BUY
            confidence = 70.0
            evidence = 75.0
            reasoning = [
                "price_above_ma20",
                "ma20_above_ma50",
            ]
        elif price < ma_fast < ma_slow:
            action = Action.SELL
            confidence = 70.0
            evidence = 75.0
            reasoning = [
                "price_below_ma20",
                "ma20_below_ma50",
            ]
        else:
            action = Action.HOLD
            confidence = 55.0
            evidence = 50.0
            reasoning = ["mixed_market_trend"]

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

    def _momentum_analysis(
        self,
        *,
        symbol: str,
        closes: list[float],
    ) -> AnalysisResult:
        """Short-horizon momentum from rate-of-change."""

        lookback = min(self.MOMENTUM_LOOKBACK, len(closes) - 1)
        if lookback <= 0:
            return AnalysisResult(
                analyst="technical:momentum",
                symbol=symbol,
                action=Action.HOLD,
                confidence=50.0,
                evidence=40.0,
                reasoning=["insufficient_momentum_history"],
                signal_confidence=50.0,
            )

        start = closes[-lookback - 1]
        price = closes[-1]
        if start <= 0:
            roc = 0.0
        else:
            roc = (price - start) / start * 100.0

        if roc >= 3.0:
            action = Action.BUY
            confidence = min(85.0, 60.0 + roc)
            evidence = min(90.0, 55.0 + abs(roc) * 2.0)
            reasoning = [f"positive_momentum_{roc:.2f}pct"]
        elif roc <= -3.0:
            action = Action.SELL
            confidence = min(85.0, 60.0 + abs(roc))
            evidence = min(90.0, 55.0 + abs(roc) * 2.0)
            reasoning = [f"negative_momentum_{roc:.2f}pct"]
        else:
            action = Action.HOLD
            confidence = 55.0
            evidence = 45.0
            reasoning = [f"neutral_momentum_{roc:.2f}pct"]

        return AnalysisResult(
            analyst="technical:momentum",
            symbol=symbol,
            action=action,
            confidence=round(confidence, 2),
            evidence=round(evidence, 2),
            reasoning=reasoning,
            signal_confidence=round(confidence, 2),
            metadata={"roc_pct": roc, "lookback": lookback},
        )

    def _volume_analysis(
        self,
        *,
        symbol: str,
        closes: list[float],
        volumes: list[float],
    ) -> AnalysisResult:
        """Volume confirmation relative to recent average.

        Volume does not invent direction alone; it follows short-term
        price change and scales confidence/evidence.
        """

        lookback = min(self.VOLUME_LOOKBACK, len(volumes))
        recent = volumes[-lookback:]
        average_volume = sum(recent) / lookback if lookback else 0.0
        volume = volumes[-1]
        volume_ratio = (
            volume / average_volume if average_volume > 0 else 1.0
        )

        price_change = 0.0
        if len(closes) >= 2 and closes[-2] > 0:
            price_change = (closes[-1] - closes[-2]) / closes[-2] * 100.0

        if volume_ratio >= 1.5 and price_change > 0:
            action = Action.BUY
            confidence = min(80.0, 55.0 + volume_ratio * 8.0)
            evidence = min(85.0, 50.0 + volume_ratio * 10.0)
            reasoning = [
                f"volume_{volume_ratio:.2f}x_average",
                "volume_supports_up_move",
            ]
        elif volume_ratio >= 1.5 and price_change < 0:
            action = Action.SELL
            confidence = min(80.0, 55.0 + volume_ratio * 8.0)
            evidence = min(85.0, 50.0 + volume_ratio * 10.0)
            reasoning = [
                f"volume_{volume_ratio:.2f}x_average",
                "volume_supports_down_move",
            ]
        elif volume_ratio < 0.75:
            action = Action.HOLD
            confidence = 50.0
            evidence = 40.0
            reasoning = [
                f"low_volume_{volume_ratio:.2f}x_average",
            ]
        else:
            action = Action.HOLD
            confidence = 55.0
            evidence = 45.0
            reasoning = [
                f"normal_volume_{volume_ratio:.2f}x_average",
            ]

        return AnalysisResult(
            analyst="technical:volume",
            symbol=symbol,
            action=action,
            confidence=round(confidence, 2),
            evidence=round(evidence, 2),
            reasoning=reasoning,
            signal_confidence=round(confidence, 2),
            metadata={
                "volume_ratio": volume_ratio,
                "price_change_pct": price_change,
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
