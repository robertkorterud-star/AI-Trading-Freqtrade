from atlas.models.action import Action
from atlas.trading.expected_return_model import ExpectedReturnModel
from atlas.trading.expected_return_service import ExpectedReturnService


class FakeProvider:
    def __init__(self, returns):
        self.returns = returns
        self.calls = []

    def get_returns(self, symbol, action):
        self.calls.append((symbol, action))
        return self.returns


def test_service_passes_provider_history_to_model():
    provider = FakeProvider([0.02] * 10)
    model = ExpectedReturnModel(haircut=0.5)
    service = ExpectedReturnService(provider, model)

    result = service.estimate("BTCUSDT", Action.BUY)

    assert result == 0.01
    assert provider.calls == [("BTCUSDT", Action.BUY)]


def test_service_returns_zero_when_history_is_insufficient():
    provider = FakeProvider([0.02] * 9)
    service = ExpectedReturnService(provider)

    assert service.estimate("BTCUSDT", Action.BUY) == 0.0


def test_service_handles_sell_direction():
    provider = FakeProvider([-0.02] * 10)
    model = ExpectedReturnModel(haircut=0.5)
    service = ExpectedReturnService(provider, model)

    assert service.estimate("BTCUSDT", Action.SELL) == 0.01


def test_service_handles_hold():
    provider = FakeProvider([0.02] * 10)
    service = ExpectedReturnService(provider)

    assert service.estimate("BTCUSDT", Action.HOLD) == 0.0
