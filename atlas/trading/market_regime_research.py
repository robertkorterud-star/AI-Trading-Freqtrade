"""
ATLAS Market Regime Research.

Research-only analysis of historical market regimes.

Regimes are classified using only candles available at the
classification timestamp. Forward returns are measured after
the regime has been classified, preventing look-ahead bias.
"""

from dataclasses import dataclass

from atlas.trading.historical_market_data import (
    HistoricalMarketData,
)
from atlas.trading.indicator_engine import (
    IndicatorEngine,
)
from atlas.trading.market_regime import (
    MarketRegimeAnalyzer,
)


@dataclass(frozen=True, slots=True)
class MarketRegimeObservation:
    index: int
    regime: str
    confidence: float
    trend_strength: float
    volatility_level: str
    forward_return_percent: float | None


@dataclass(frozen=True, slots=True)
class MarketRegimeResult:
    symbol: str
    timeframe: str
    source: str

    observations: tuple[MarketRegimeObservation, ...]

    regime_counts: tuple[tuple[str, int], ...]
    regime_average_forward_returns: tuple[
        tuple[str, float], ...
    ]

    classified_observations: int

    @property
    def regime_distribution(
        self,
    ) -> dict[str, int]:
        return dict(self.regime_counts)

    @property
    def average_forward_returns(
        self,
    ) -> dict[str, float]:
        return dict(
            self.regime_average_forward_returns
        )


class MarketRegimeResearch:
    """Research historical market regimes without look-ahead."""

    def __init__(
        self,
        forward_period: int = 1,
    ):
        if forward_period <= 0:
            raise ValueError(
                "forward_period must be positive."
            )

        self.forward_period = forward_period
        self.indicator_engine = IndicatorEngine()
        self.regime_analyzer = MarketRegimeAnalyzer()

    def run(
        self,
        data: HistoricalMarketData,
    ) -> MarketRegimeResult:

        closes = data.closes

        observations = []

        if len(closes) < 2:
            return self._result(
                data,
                observations,
            )

        for index in range(
            len(closes) - 1
        ):

            candles = [
                {
                    "close": bar.close,
                    "high": bar.high,
                    "low": bar.low,
                    "volume": bar.volume,
                }
                for bar in data.bars[
                    : index + 1
                ]
            ]

            indicators = (
                self.indicator_engine.calculate(
                    candles
                )
            )

            regime = (
                self.regime_analyzer.analyze(
                    indicators
                )
            )

            forward_index = (
                index
                + self.forward_period
            )

            if forward_index < len(closes):
                forward_return = (
                    (
                        closes[forward_index]
                        / closes[index]
                    )
                    - 1.0
                ) * 100.0
            else:
                forward_return = None

            observations.append(
                MarketRegimeObservation(
                    index=index,
                    regime=regime.regime,
                    confidence=regime.confidence,
                    trend_strength=(
                        regime.trend_strength
                    ),
                    volatility_level=(
                        regime.volatility_level
                    ),
                    forward_return_percent=(
                        forward_return
                    ),
                )
            )

        return self._result(
            data,
            observations,
        )

    @staticmethod
    def _result(
        data: HistoricalMarketData,
        observations: list[
            MarketRegimeObservation
        ],
    ) -> MarketRegimeResult:

        regime_counts: dict[str, int] = {}

        forward_returns: dict[
            str,
            list[float],
        ] = {}

        for observation in observations:

            if observation.regime == "UNKNOWN":
                continue

            regime_counts[
                observation.regime
            ] = (
                regime_counts.get(
                    observation.regime,
                    0,
                )
                + 1
            )

            if (
                observation.forward_return_percent
                is not None
            ):
                forward_returns.setdefault(
                    observation.regime,
                    [],
                ).append(
                    observation.forward_return_percent
                )

        average_returns = {}

        for regime, values in (
            forward_returns.items()
        ):
            if values:
                average_returns[regime] = (
                    sum(values)
                    / len(values)
                )

        return MarketRegimeResult(
            symbol=data.symbol,
            timeframe=data.timeframe,
            source=data.source,
            observations=tuple(
                observations
            ),
            regime_counts=tuple(
                sorted(
                    regime_counts.items()
                )
            ),
            regime_average_forward_returns=tuple(
                sorted(
                    (
                        regime,
                        value,
                    )
                    for regime, value
                    in average_returns.items()
                )
            ),
            classified_observations=sum(
                regime_counts.values()
            ),
        )
