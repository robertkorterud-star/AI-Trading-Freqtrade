from atlas.agents import (
    MomentumAgent,
    TrendAgent,
    VolumeAgent,
    VolatilityAgent,
)
from atlas.trading.dry_run_loop import DryRunLoop
from atlas.trading.market_data import Candle, MarketSnapshot


def snapshot():
    return MarketSnapshot(
        symbol="BTC-USD",
        timestamp=4,
        price=108.0,
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
                close=106,
                volume=1500,
            ),
            Candle(
                timestamp=4,
                open=106,
                high=110,
                low=105,
                close=108,
                volume=1700,
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


def test_complete_atlas_pipeline_runs_end_to_end():
    loop = DryRunLoop(agents=agents())

    result = loop.process(snapshot())

    assert result.symbol == "BTC-USD"
    assert result.price == 108.0

    assert len(result.observations) == 4

    assert -1.0 <= result.intelligence_score <= 1.0
    assert 0.0 <= result.intelligence_confidence <= 1.0

    assert result.decision is not None
    assert result.execution is not None

    assert result.execution.symbol == "BTC-USD"
    assert result.execution.price == 108.0


def test_pipeline_preserves_all_agent_observations():
    loop = DryRunLoop(agents=agents())

    result = loop.process(snapshot())

    names = {
        observation.agent
        for observation in result.observations
    }

    assert names == {
        "trend",
        "momentum",
        "volume",
        "volatility",
    }


def test_pipeline_produces_a_valid_final_decision():
    loop = DryRunLoop(agents=agents())

    result = loop.process(snapshot())

    decision = result.decision

    assert decision.action is not None
    assert -1.0 <= decision.score <= 1.0
    assert 0.0 <= decision.confidence <= 1.0
    assert 0.0 <= decision.risk_score <= 1.0
    assert decision.reason


def test_pipeline_execution_is_paper_only():
    loop = DryRunLoop(agents=agents())

    result = loop.process(snapshot())

    trader = loop.trader

    assert result.execution.equity > 0.0
    assert trader.portfolio.cash >= 0.0

    assert not hasattr(trader, "exchange")
    assert not hasattr(trader, "ccxt")


def test_pipeline_can_process_multiple_cycles():
    loop = DryRunLoop(agents=agents())

    first = loop.process(snapshot())

    second_snapshot = MarketSnapshot(
        symbol="BTC-USD",
        timestamp=5,
        price=112.0,
        candles=(
            *snapshot().candles,
            Candle(
                timestamp=5,
                open=108,
                high=113,
                low=107,
                close=112,
                volume=1900,
            ),
        ),
    )

    second = loop.process(second_snapshot)

    assert first.symbol == second.symbol == "BTC-USD"
    assert second.price == 112.0
    assert second.execution.equity > 0.0
