"""ATLAS multi-horizon decision engine."""

from dataclasses import dataclass
from atlas.market.trading_horizon import TradingHorizon
from atlas.models.action import Action


@dataclass(frozen=True, slots=True)
class HorizonSignal:
    """Directional signal for one trading horizon."""

    horizon: TradingHorizon
    action: Action
    score: float
    confidence: float

    def __post_init__(self):
        if not 0.0 <= self.score <= 100.0:
            raise ValueError("score must be between 0 and 100")

        if not 0.0 <= self.confidence <= 100.0:
            raise ValueError("confidence must be between 0 and 100")


@dataclass(frozen=True, slots=True)
class MultiHorizonResult:
    """Final decision across multiple trading horizons."""

    symbol: str
    action: Action
    score: float
    confidence: float
    alignment: float
    signals: tuple[HorizonSignal, ...]
    reasoning: list[str]


class MultiHorizonDecisionEngine:
    """Combine short, medium and long horizon signals."""

    name = "multi_horizon_decision"

    DEFAULT_WEIGHTS = {
        TradingHorizon.INTRADAY: 0.20,
        TradingHorizon.SWING: 0.35,
        TradingHorizon.POSITION: 0.45,
    }

    def __init__(
        self,
        weights: dict[TradingHorizon, float] | None = None,
        decision_threshold: float = 0.20,
    ):
        self.weights = dict(weights or self.DEFAULT_WEIGHTS)

        if not self.weights:
            raise ValueError("at least one horizon weight is required")

        if any(weight < 0 for weight in self.weights.values()):
            raise ValueError("horizon weights must be non-negative")

        total_weight = sum(self.weights.values())

        if total_weight <= 0:
            raise ValueError("horizon weights must have positive total weight")

        if not 0.0 <= decision_threshold <= 1.0:
            raise ValueError("decision_threshold must be between 0 and 1")

        self._total_weight = total_weight
        self.decision_threshold = decision_threshold

    def decide(
        self,
        symbol: str,
        signals: list[HorizonSignal],
    ) -> MultiHorizonResult:
        """Produce a directional decision from horizon signals."""

        if not signals:
            raise ValueError(
                "at least one horizon signal is required"
            )

        if any(
            signal.horizon not in self.weights
            for signal in signals
        ):
            raise ValueError(
                "all signal horizons must have configured weights"
            )

        if len(
            {signal.horizon for signal in signals}
        ) != len(signals):
            raise ValueError(
                "each horizon may only appear once"
            )

        directional_values = []

        for signal in signals:
            direction = self._direction(signal.action)

            strength = (
                (signal.score - 50.0) / 50.0
            )

            directional_values.append(
                (
                    signal.horizon,
                    direction * abs(strength),
                    self.weights[signal.horizon],
                )
            )

        weighted_direction = (
            sum(
                direction * weight
                for _, direction, weight in directional_values
            )
            / self._total_weight
        )

        if weighted_direction >= self.decision_threshold:
            action = Action.BUY
        elif weighted_direction <= -self.decision_threshold:
            action = Action.SELL
        else:
            action = Action.HOLD

        score = round(
            50.0 + weighted_direction * 50.0,
            4,
        )

        alignment = self._alignment(signals)

        average_confidence = (
            sum(
                signal.confidence * self.weights[signal.horizon]
                for signal in signals
            )
            / sum(
                self.weights[signal.horizon]
                for signal in signals
            )
        )

        confidence = round(
            min(
                100.0,
                50.0
                + (
                    alignment * 20.0
                )
                + (
                    abs(weighted_direction) * 30.0
                )
                + (
                    (average_confidence - 50.0) * 0.20
                ),
            ),
            4,
        )

        reasoning = [
            f"{self.name}: evaluated {len(signals)} horizons.",
            f"Weighted directional score: {weighted_direction:.4f}.",
            f"Horizon alignment: {alignment:.4f}.",
            f"Final action: {action.value}.",
        ]

        for signal in signals:
            reasoning.append(
                f"{signal.horizon.value}: "
                f"{signal.action.value}, "
                f"score={signal.score:.2f}, "
                f"confidence={signal.confidence:.2f}."
            )

        return MultiHorizonResult(
            symbol=symbol,
            action=action,
            score=score,
            confidence=confidence,
            alignment=alignment,
            signals=tuple(signals),
            reasoning=reasoning,
        )

    @staticmethod
    def _direction(action: Action) -> float:
        if action is Action.BUY:
            return 1.0

        if action is Action.SELL:
            return -1.0

        return 0.0

    @staticmethod
    def _alignment(
        signals: list[HorizonSignal],
    ) -> float:
        if not signals:
            return 0.0

        buy = sum(
            signal.action is Action.BUY
            for signal in signals
        )

        sell = sum(
            signal.action is Action.SELL
            for signal in signals
        )

        hold = sum(
            signal.action is Action.HOLD
            for signal in signals
        )

        majority = max(
            buy,
            sell,
            hold,
        )

        return round(
            majority / len(signals),
            4,
        )
