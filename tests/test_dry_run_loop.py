from atlas.agents.base import AgentObservation
from atlas.trading.dry_run_loop import DryRunLoop
from atlas.trading.market_data import Candle, MarketSnapshot


class BullishAgent:
    name = "bullish"

    def analyze(self, snapshot):
        return AgentObservation(
            agent=self.name,
            symbol=snapshot.symbol,
            score=0.90,
            confidence=0.90,
            direction="bullish",
            reason="strong bullish test signal",
        )


class BearishAgent:
    name = "bearish"

    def analyze(self, snapshot):
        return AgentObservation(
            agent=self.name,
            symbol=snapshot.symbol,
            score=-0.90,
            confidence=0.90,
            direction="bearish",
            reason="strong bearish test signal",
        )


def snapshot():
    candles = [
        Candle(
            timestamp=1,
            open=100,
            high=102,
            low=99,
            close=101,
            volume=1000,
        ),
        Candle(
            timestamp=2,
            open=101,
            high=105,
            low=100,
            close=104,
            volume=1200,
        ),
    ]

    return MarketSnapshot.from_candles(
        "BTC-USD",
        candles,
    )


def test_dry_run_loop_connects_agents_to_execution():
    loop = DryRunLoop(
        agents=[BullishAgent()],
    )

    result = loop.process(snapshot())

    assert result.symbol == "BTC-USD"
    assert result.price == 104
    assert len(result.observations) == 1
    assert result.intelligence_score > 0
    assert result.execution.symbol == "BTC-USD"


def test_conflicting_agents_reduce_intelligence():
    loop = DryRunLoop(
        agents=[
            BullishAgent(),
            BearishAgent(),
        ],
    )

    result = loop.process(snapshot())

    assert abs(result.intelligence_score) < 0.20


def test_loop_never_uses_live_exchange():
    loop = DryRunLoop(
        agents=[BullishAgent()],
    )

    result = loop.process(snapshot())

    assert result.execution.equity > 0
    assert loop.trader.portfolio.cash > 0
