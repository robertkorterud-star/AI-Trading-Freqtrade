import pytest

from datetime import datetime, timedelta

from atlas.trading.historical_market_data import (
    HistoricalMarketData,
    OHLCVBar,
)
from atlas.trading.regime_strategy_research import (
    RegimeStrategyResearch,
    RegimeStrategyResearchSummary,
)


def _data(
    closes=None,
):
    if closes is None:
        closes = [
            100.0,
            100.0,
            100.0,
            100.0,
            100.0,
            95.0,
            96.0,
            97.0,
            98.0,
            99.0,
            100.0,
            101.0,
            102.0,
            103.0,
            104.0,
            100.0,
            99.0,
            98.0,
            97.0,
            96.0,
            95.0,
            96.0,
            97.0,
            98.0,
            99.0,
            100.0,
            101.0,
            102.0,
            103.0,
            104.0,
            105.0,
            106.0,
            107.0,
            108.0,
            109.0,
            110.0,
            111.0,
            112.0,
            113.0,
            114.0,
        ]

    bars = []

    for index, close in enumerate(closes):
        previous = (
            closes[index - 1]
            if index
            else close
        )

        bars.append(
            OHLCVBar(
                timestamp=(
                    datetime(2026, 1, 1)
                    + timedelta(hours=index)
                ),
                open=previous,
                high=max(previous, close) + 1.0,
                low=min(previous, close) - 1.0,
                close=close,
                volume=1000.0,
            )
        )

    return HistoricalMarketData(
        symbol="BTC-USD",
        bars=bars,
        timeframe="4h",
        source="test",
    )


def test_research_returns_summary():
    result = (
        RegimeStrategyResearch()
        .run(_data())
    )

    assert isinstance(
        result,
        RegimeStrategyResearchSummary,
    )


def test_all_strategy_families_are_present():
    result = (
        RegimeStrategyResearch()
        .run(_data())
    )

    names = {
        item.strategy_name
        for item in result.results
    }

    assert names == {
        "Trend Following",
        "Mean Reversion",
        "Momentum",
    }


def test_mean_reversion_has_real_trade_observations():
    result = (
        RegimeStrategyResearch()
        .run(_data())
    )

    mean_reversion = next(
        item
        for item in result.results
        if item.strategy_name
        == "Mean Reversion"
    )

    assert mean_reversion.classified_observations > 0
    assert sum(
        mean_reversion.regime_counts.values()
    ) == mean_reversion.classified_observations


def test_observations_match_regime_counts():
    result = (
        RegimeStrategyResearch()
        .run(_data())
    )

    for strategy in result.results:
        assert sum(
            strategy.regime_counts.values()
        ) == strategy.classified_observations


def test_average_returns_match_observations():
    result = (
        RegimeStrategyResearch()
        .run(_data())
    )

    for strategy in result.results:
        for regime, average in (
            strategy.average_forward_returns.items()
        ):
            values = [
                observation.forward_return_percent
                for observation in strategy.observations
                if observation.regime == regime
            ]

            assert values

            assert average == pytest.approx(
                sum(values) / len(values),
                abs=1e-10,
            )


def test_best_strategy_by_regime_is_consistent():
    result = (
        RegimeStrategyResearch()
        .run(_data())
    )

    for regime, strategy_name in (
        result.best_strategy_by_regime.items()
    ):
        candidates = [
            item
            for item in result.results
            if regime
            in item.average_forward_returns
        ]

        assert candidates

        winner = max(
            candidates,
            key=lambda item: (
                item.average_forward_returns[
                    regime
                ],
                item.regime_counts.get(
                    regime,
                    0,
                ),
                item.strategy_name,
            ),
        )

        assert (
            strategy_name
            == winner.strategy_name
        )


def test_overall_best_strategy_is_present():
    result = (
        RegimeStrategyResearch()
        .run(_data())
    )

    assert (
        result.overall_best_strategy
        in {
            "Trend Following",
            "Mean Reversion",
            "Momentum",
        }
    )


def test_short_dataset_returns_empty_summary():
    result = (
        RegimeStrategyResearch()
        .run(
            _data(
                [
                    100.0,
                    101.0,
                    102.0,
                ]
            )
        )
    )

    assert result.results == ()
    assert result.overall_best_strategy is None
    assert result.best_strategy_by_regime == {}


def test_research_is_deterministic():
    data = _data()

    research = RegimeStrategyResearch()

    first = research.run(data)
    second = research.run(data)

    assert first == second
