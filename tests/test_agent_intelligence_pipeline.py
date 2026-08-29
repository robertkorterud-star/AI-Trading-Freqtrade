from atlas.agents import (
    MomentumAgent,
    TrendAgent,
    VolumeAgent,
    VolatilityAgent,
)
from atlas.agents.intelligence import MarketIntelligence
from atlas.trading.market_data import Candle, MarketSnapshot


def snapshot():
    return MarketSnapshot(
        symbol="BTC-USD",
        timestamp=3,
        price=106,
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
        ),
    )


def test_builtin_agents_are_available():
    agents = [
        TrendAgent(),
        MomentumAgent(),
        VolumeAgent(),
        VolatilityAgent(),
    ]

    assert len(agents) == 4
    assert all(agent.name for agent in agents)
    assert all(agent.category for agent in agents)


def test_market_intelligence_aggregates_builtin_agents():
    intelligence = MarketIntelligence(
        agents=[
            TrendAgent(),
            MomentumAgent(),
            VolumeAgent(),
            VolatilityAgent(),
        ]
    )

    result = intelligence.analyze(snapshot())

    assert result
    assert len(result.observations) == 4
    assert all(observation.symbol == "BTC-USD" for observation in result.observations)


def test_market_intelligence_preserves_agent_identity():
    intelligence = MarketIntelligence(
        agents=[
            TrendAgent(),
            MomentumAgent(),
            VolumeAgent(),
            VolatilityAgent(),
        ]
    )

    result = intelligence.analyze(snapshot())

    names = {observation.agent for observation in result.observations}

    assert "trend" in names
    assert "momentum" in names
    assert "volume" in names
    assert "volatility" in names


def test_market_intelligence_produces_normalized_observations():
    intelligence = MarketIntelligence(
        agents=[
            TrendAgent(),
            MomentumAgent(),
            VolumeAgent(),
            VolatilityAgent(),
        ]
    )

    result = intelligence.analyze(snapshot())

    for observation in result.observations:
        assert -1.0 <= observation.score <= 1.0
        assert 0.0 <= observation.confidence <= 1.0
        assert observation.direction
