"""ATLAS signal fusion."""

from dataclasses import dataclass

from atlas.algorithms.base import AlgorithmSignal
from atlas.models.action import Action


@dataclass(frozen=True, slots=True)
class FusionResult:
    """Combined result from multiple algorithm signals."""

    symbol: str
    timeframe: str
    action: Action
    score: float
    confidence: float
    agreement: float
    signals: tuple[AlgorithmSignal, ...]
    reasoning: list[str]


class SignalFusion:
    """Combine independent algorithm signals deterministically."""

    name = "signal_fusion"

    def __init__(
        self,
        buy_threshold: float = 0.60,
        sell_threshold: float = 0.60,
    ):
        if not 0.0 <= buy_threshold <= 1.0:
            raise ValueError("buy_threshold must be between 0 and 1")

        if not 0.0 <= sell_threshold <= 1.0:
            raise ValueError("sell_threshold must be between 0 and 1")

        self.buy_threshold = buy_threshold
        self.sell_threshold = sell_threshold

    def combine(
        self,
        signals: list[AlgorithmSignal],
    ) -> FusionResult:
        if not signals:
            raise ValueError(
                "at least one algorithm signal is required"
            )

        symbol = signals[0].symbol
        timeframe = signals[0].timeframe

        if any(signal.symbol != symbol for signal in signals):
            raise ValueError("all signals must use the same symbol")

        if any(signal.timeframe != timeframe for signal in signals):
            raise ValueError("all signals must use the same timeframe")

        effective_signals = self._effective_signals(signals)

        buy_count = sum(
            signal.action is Action.BUY
            for signal in effective_signals
        )
        sell_count = sum(
            signal.action is Action.SELL
            for signal in effective_signals
        )
        hold_count = sum(
            signal.action is Action.HOLD
            for signal in effective_signals
        )

        total = len(effective_signals)

        buy_ratio = buy_count / total
        sell_ratio = sell_count / total

        if buy_ratio >= self.buy_threshold and buy_count > sell_count:
            action = Action.BUY
        elif (
            sell_ratio >= self.sell_threshold
            and sell_count > buy_count
        ):
            action = Action.SELL
        else:
            action = Action.HOLD

        weighted_score = sum(
            self._direction_score(signal)
            for signal in effective_signals
        ) / total

        score = round(
            50.0 + weighted_score * 50.0,
            4,
        )

        majority_count = max(
            buy_count,
            sell_count,
            hold_count,
        )

        agreement = round(
            majority_count / total,
            4,
        )

        confidence = round(
            50.0 + agreement * 40.0,
            4,
        )

        reasoning = [
            f"{self.name}: combined {total} algorithm signals.",
            f"BUY signals: {buy_count}.",
            f"HOLD signals: {hold_count}.",
            f"SELL signals: {sell_count}.",
            f"Algorithm agreement: {agreement:.4f}.",
        ]

        if action is Action.BUY:
            reasoning.append(
                "BUY has sufficient algorithm agreement."
            )
        elif action is Action.SELL:
            reasoning.append(
                "SELL has sufficient algorithm agreement."
            )
        else:
            reasoning.append(
                "No directional consensus reached."
            )

        return FusionResult(
            symbol=symbol,
            timeframe=timeframe,
            action=action,
            score=score,
            confidence=confidence,
            agreement=agreement,
            signals=tuple(signals),
            reasoning=reasoning,
        )

    @staticmethod
    def _effective_signals(
        signals: list[AlgorithmSignal],
    ) -> list[AlgorithmSignal]:
        """Collapse correlated evidence families into one effective signal."""

        grouped: dict[str, list[AlgorithmSignal]] = {}
        effective: list[AlgorithmSignal] = []

        for signal in signals:
            if signal.evidence_family is None:
                effective.append(signal)
                continue

            grouped.setdefault(
                signal.evidence_family,
                [],
            ).append(signal)

        for family, family_signals in grouped.items():
            if len(family_signals) == 1:
                effective.append(family_signals[0])
                continue

            buy_count = sum(
                signal.action is Action.BUY
                for signal in family_signals
            )
            sell_count = sum(
                signal.action is Action.SELL
                for signal in family_signals
            )
            hold_count = sum(
                signal.action is Action.HOLD
                for signal in family_signals
            )

            counts = {
                Action.BUY: buy_count,
                Action.SELL: sell_count,
                Action.HOLD: hold_count,
            }
            highest = max(counts.values())
            winners = [
                action
                for action, count in counts.items()
                if count == highest
            ]

            action = (
                winners[0]
                if len(winners) == 1
                else Action.HOLD
            )

            directional = [
                signal
                for signal in family_signals
                if signal.action is action
            ]
            score_source = (
                directional
                if directional
                else family_signals
            )
            score = sum(
                signal.score
                for signal in score_source
            ) / len(score_source)
            confidence = sum(
                signal.confidence
                for signal in family_signals
            ) / len(family_signals)

            effective.append(
                AlgorithmSignal(
                    algorithm=f"evidence_family:{family}",
                    symbol=family_signals[0].symbol,
                    timeframe=family_signals[0].timeframe,
                    action=action,
                    score=score,
                    confidence=confidence,
                    evidence_family=family,
                    reasoning=[
                        f"Combined {len(family_signals)} "
                        f"signals from evidence family {family}."
                    ],
                )
            )

        return effective

    @staticmethod
    def _direction_score(
        signal: AlgorithmSignal,
    ) -> float:
        """Convert a signal score into a directional contribution."""

        normalized = (signal.score - 50.0) / 50.0

        if signal.action is Action.BUY:
            return normalized

        if signal.action is Action.SELL:
            return -normalized

        return 0.0
