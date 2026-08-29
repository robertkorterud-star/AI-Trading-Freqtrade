from atlas.agents import (
    MomentumAgent,
    TrendAgent,
    VolumeAgent,
    VolatilityAgent,
)
from atlas.trading.dry_run_loop import DryRunLoop
from atlas.trading.market_data import Candle, MarketSnapshot


def snapshot(price=106):
    return MarketSnapshot(
        symbol="BTC-USD",
        timestamp=3,
        price=price,
        candles=(
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
            Candle(
                timestamp=3,
                open=104,
                high=108,
                low=103,
                close=price,
                volume=1500,
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


def test_dry_run_cycle_contains_learning_observations():
    result = DryRunLoop(agents=agents()).process(snapshot())

    assert result.symbol == "BTC-USD"
    assert result.price == 106
    assert len(result.observations) == 4

    for observation in result.observations:
        assert observation.agent
        assert observation.symbol == "BTC-USD"
        assert observation.direction
        assert -1.0 <= observation.score <= 1.0
        assert 0.0 <= observation.confidence <= 1.0


def test_dry_run_cycle_contains_intelligence_state():
    result = DryRunLoop(agents=agents()).process(snapshot())

    assert -1.0 <= result.intelligence_score <= 1.0
    assert 0.0 <= result.intelligence_confidence <= 1.0


def test_dry_run_cycle_contains_final_decision():
    result = DryRunLoop(agents=agents()).process(snapshot())

    assert result.decision is not None
    assert result.decision.action is not None
    assert result.decision.reason is not None


def test_dry_run_cycle_contains_execution_result():
    result = DryRunLoop(agents=agents()).process(snapshot())

    assert result.execution is not None


def test_multiple_cycles_produce_distinct_market_states():
    loop = DryRunLoop(agents=agents())

    first = loop.process(snapshot(106))
    second = loop.process(snapshot(110))

    assert first.price == 106
    assert second.price == 110
    assert first.symbol == second.symbol == "BTC-USD"
