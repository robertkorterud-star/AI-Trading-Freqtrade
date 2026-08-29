from atlas.agents import (
    AgentObservation,
    AgentRegistry,
    MarketIntelligence,
    PriceActionAgent,
)


def observation(
    score: float,
    confidence: float,
    agent: str = "test",
) -> AgentObservation:
    return AgentObservation(
        agent=agent,
        symbol="BTC-USD",
        timestamp="1",
        category="technical",
        score=score,
        confidence=confidence,
        direction=(
            "bullish"
            if score > 0
            else "bearish"
            if score < 0
            else "neutral"
        ),
    )


def test_agent_observation_serializes():
    result = observation(0.5, 0.8)

    data = result.as_dict()

    assert data["agent"] == "test"
    assert data["score"] == 0.5
    assert data["confidence"] == 0.8


def test_registry_registers_agent():
    registry = AgentRegistry()
    agent = PriceActionAgent()

    registry.register(agent)

    assert registry.get("price_action") is agent
    assert registry.all() == (agent,)


def test_registry_rejects_duplicate_agent():
    registry = AgentRegistry()

    registry.register(PriceActionAgent())

    try:
        registry.register(PriceActionAgent())
        assert False
    except ValueError:
        assert True


def test_bullish_observations_create_bullish_intelligence():
    intelligence = MarketIntelligence()

    result = intelligence.analyze(
        "BTC-USD",
        [
            observation(0.8, 0.9, "momentum"),
            observation(0.6, 0.8, "trend"),
        ],
    )

    assert result.direction == "bullish"
    assert result.score > 0.6
    assert result.confidence > 0.8


def test_conflicting_observations_reduce_score():
    intelligence = MarketIntelligence()

    result = intelligence.analyze(
        "BTC-USD",
        [
            observation(0.9, 1.0, "momentum"),
            observation(-0.9, 1.0, "mean_reversion"),
        ],
    )

    assert result.direction == "neutral"
    assert abs(result.score) < 0.01


def test_empty_intelligence_is_neutral():
    result = MarketIntelligence().analyze(
        "BTC-USD",
        [],
    )

    assert result.direction == "neutral"
    assert result.score == 0.0
    assert result.confidence == 0.0


def test_price_action_agent_detects_rising_price():
    agent = PriceActionAgent()

    result = agent.observe(
        "BTC-USD",
        {
            "candles": [
                {"timestamp": "1", "close": 100.0},
                {"timestamp": "2", "close": 105.0},
            ]
        },
    )

    assert result.direction == "bullish"
    assert result.score > 0.0
    assert result.confidence > 0.0


def test_price_action_agent_handles_missing_data():
    agent = PriceActionAgent()

    result = agent.observe(
        "BTC-USD",
        {"candles": []},
    )

    assert result.direction == "neutral"
    assert result.confidence == 0.0
