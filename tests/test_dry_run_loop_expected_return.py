from atlas.models.action import Action
from atlas.trading.dry_run_loop import DryRunLoop
from atlas.trading.dry_run_trader import DryRunResult
from atlas.trading.market_data import Candle, MarketSnapshot


class BullishAgent:
    name = "bullish"

    def analyze(self, snapshot):
        from atlas.agents.base import AgentObservation

        return AgentObservation(
            agent=self.name,
            symbol=snapshot.symbol,
            score=0.90,
            confidence=0.90,
            direction="bullish",
            reason="strong bullish test signal",
        )


class RecordingExpectedReturnService:
    def __init__(self, expected_return=0.008):
        self.expected_return = expected_return
        self.calls = []

    def estimate(self, *, symbol, action):
        self.calls.append((symbol, action))
        return self.expected_return


class RecordingTrader:
    def __init__(self):
        self.expected_returns = []

    def process_signal(self, **kwargs):
        self.expected_returns.append(kwargs["expected_return"])
        return DryRunResult(
            symbol=kwargs["symbol"],
            action=Action.HOLD,
            quantity=0.0,
            price=kwargs["price"],
            target_position=0.0,
            realized_pnl=0.0,
            equity=100_000.0,
            reason="test",
            executed=False,
        )


def snapshot():
    candles = [
        Candle(
            timestamp=i,
            open=100 + (i - 1) * 0.15,
            high=101 + (i - 1) * 0.15,
            low=99 + (i - 1) * 0.15,
            close=100 + (i - 1) * 0.15,
            volume=1000 + i * 100,
        )
        for i in range(1, 23)
    ]
    candles.append(
        Candle(
            timestamp=23,
            open=103,
            high=105,
            low=102,
            close=104,
            volume=3300,
        )
    )
    return MarketSnapshot.from_candles("BTC-USD", candles)


def test_dry_run_loop_passes_expected_return_to_trader():
    service = RecordingExpectedReturnService(expected_return=0.008)
    trader = RecordingTrader()

    loop = DryRunLoop(
        agents=[BullishAgent()],
        expected_return_service=service,
        trader=trader,
    )

    result = loop.process(snapshot())

    assert result.expected_return == 0.008
    assert trader.expected_returns == [0.008]
    assert service.calls == [("BTC-USD", Action.BUY)]


def test_dry_run_loop_keeps_expected_return_optional():
    trader = RecordingTrader()

    loop = DryRunLoop(
        agents=[BullishAgent()],
        trader=trader,
    )

    result = loop.process(snapshot())

    assert result.expected_return is None
    assert trader.expected_returns == [None]
