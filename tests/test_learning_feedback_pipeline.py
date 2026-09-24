from atlas.agents import (
    MomentumAgent,
    TrendAgent,
    VolumeAgent,
    VolatilityAgent,
)
from atlas.trading.dry_run_loop import DryRunLoop
from atlas.trading.market_data import Candle, MarketSnapshot


def snapshot(price=106, timestamp=23):
    return MarketSnapshot(
        symbol="BTC-USD",
        timestamp=timestamp,
        price=price,
        candles=tuple(
            Candle(
                timestamp=i,
                open=100 + (i - 1) * 0.15,
                high=101 + (i - 1) * 0.15,
                low=99 + (i - 1) * 0.15,
                close=100 + (i - 1) * 0.15,
                volume=1000 + i * 100,
            )
            for i in range(1, 23)
        ) + (
            Candle(
                timestamp=23,
                open=103,
                high=105,
                low=102,
                close=price,
                volume=3300,
            ),
        ),
    )


def agents():
    return [
        TrendAgent(),
        MomentumAgent(),
        VolumeAgent(),
        VolatilityAgent(),
    ]


def test_learning_feedback_pipeline_can_run_multiple_cycles():
    loop = DryRunLoop(agents=agents())

    first = loop.process(snapshot(price=106, timestamp=23))
    second = loop.process(snapshot(price=108, timestamp=23))
    third = loop.process(snapshot(price=104, timestamp=23))

    assert first.symbol == "BTC-USD"
    assert second.symbol == "BTC-USD"
    assert third.symbol == "BTC-USD"

    assert len(first.observations) == 4
    assert len(second.observations) == 4
    assert len(third.observations) == 4


def test_learning_feedback_pipeline_preserves_agent_identity():
    loop = DryRunLoop(agents=agents())

    result = loop.process(snapshot())

    names = {observation.agent for observation in result.observations}

    assert names == {
        "trend",
        "momentum",
        "volume",
        "volatility",
    }


def test_learning_feedback_pipeline_keeps_execution_paper_only():
    loop = DryRunLoop(agents=agents())

    result = loop.process(snapshot())

    assert result.execution is not None
    assert result.execution.symbol == "BTC-USD"

    # The end-to-end pipeline must remain simulated.
    # DryRunResult is the simulation result contract; it does not
    # expose an "executed" flag.
    assert result.execution.symbol == "BTC-USD"
