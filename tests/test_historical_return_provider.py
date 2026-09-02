from dataclasses import dataclass

import pytest

from atlas.models.action import Action
from atlas.trading.historical_return_provider import (
    HistoricalReturnProvider,
)


@dataclass
class FakePrediction:
    symbol: str
    action: str
    price_change_percent: float | None


class FakeRepository:
    def __init__(self, predictions):
        self.predictions = predictions

    def get_evaluated(self):
        return self.predictions


def test_returns_matching_symbol_and_action():
    repository = FakeRepository(
        [
            FakePrediction("BTCUSDT", "BUY", 2.0),
            FakePrediction("BTCUSDT", "BUY", 4.0),
            FakePrediction("ETHUSDT", "BUY", 8.0),
            FakePrediction("BTCUSDT", "SELL", -3.0),
        ]
    )

    provider = HistoricalReturnProvider(repository)

    assert provider.get_returns("BTCUSDT", Action.BUY) == [
        0.02,
        0.04,
    ]


def test_sell_history_is_returned_in_market_direction():
    repository = FakeRepository(
        [
            FakePrediction("BTCUSDT", "SELL", -2.0),
            FakePrediction("BTCUSDT", "SELL", 3.0),
        ]
    )

    provider = HistoricalReturnProvider(repository)

    assert provider.get_returns("BTCUSDT", Action.SELL) == [
        -0.02,
        0.03,
    ]


def test_hold_returns_empty_history():
    repository = FakeRepository(
        [FakePrediction("BTCUSDT", "HOLD", 5.0)]
    )

    provider = HistoricalReturnProvider(repository)

    assert provider.get_returns("BTCUSDT", Action.HOLD) == []


def test_missing_price_change_is_ignored():
    repository = FakeRepository(
        [
            FakePrediction("BTCUSDT", "BUY", None),
            FakePrediction("BTCUSDT", "BUY", 2.0),
        ]
    )

    provider = HistoricalReturnProvider(repository)

    assert provider.get_returns("BTCUSDT", Action.BUY) == [0.02]


def test_max_samples_keeps_most_recent_values():
    repository = FakeRepository(
        [
            FakePrediction("BTCUSDT", "BUY", 1.0),
            FakePrediction("BTCUSDT", "BUY", 2.0),
            FakePrediction("BTCUSDT", "BUY", 3.0),
        ]
    )

    provider = HistoricalReturnProvider(
        repository,
        max_samples=2,
    )

    assert provider.get_returns("BTCUSDT", Action.BUY) == [
        0.02,
        0.03,
    ]


def test_invalid_max_samples_is_rejected():
    with pytest.raises(ValueError, match="max_samples"):
        HistoricalReturnProvider(
            FakeRepository([]),
            max_samples=0,
        )
