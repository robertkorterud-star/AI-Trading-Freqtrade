from atlas.agents import (
    MomentumAgent,
    TrendAgent,
    VolumeAgent,
    VolatilityAgent,
)


def candles(
    closes,
    volumes=None,
):
    if volumes is None:
        volumes = [100.0] * len(closes)

    return [
        {
            "timestamp": str(index),
            "open": close,
            "high": close,
            "low": close,
            "close": close,
            "volume": volume,
        }
        for index, (close, volume)
        in enumerate(zip(closes, volumes))
    ]


def test_trend_agent_detects_uptrend():
    agent = TrendAgent()

    result = agent.observe(
        "BTC-USD",
        {
            "candles": candles(
                [100, 101, 102, 103, 104, 105, 106, 108, 110, 112]
            )
        },
    )

    assert result.direction == "bullish"
    assert result.score > 0.0
    assert result.confidence > 0.0


def test_trend_agent_detects_downtrend():
    agent = TrendAgent()

    result = agent.observe(
        "BTC-USD",
        {
            "candles": candles(
                [112, 110, 108, 106, 105, 104, 103, 102, 101, 100]
            )
        },
    )

    assert result.direction == "bearish"
    assert result.score < 0.0


def test_momentum_agent_detects_positive_momentum():
    agent = MomentumAgent()

    result = agent.observe(
        "BTC-USD",
        {
            "candles": candles(
                [100, 100, 101, 102, 103, 106]
            )
        },
    )

    assert result.direction == "bullish"
    assert result.score > 0.0


def test_momentum_agent_detects_negative_momentum():
    agent = MomentumAgent()

    result = agent.observe(
        "BTC-USD",
        {
            "candles": candles(
                [106, 105, 104, 103, 101, 100]
            )
        },
    )

    assert result.direction == "bearish"
    assert result.score < 0.0


def test_volume_agent_detects_bullish_volume_expansion():
    agent = VolumeAgent()

    result = agent.observe(
        "BTC-USD",
        {
            "candles": candles(
                [100, 100, 100, 100, 100, 105],
                [100, 100, 100, 100, 100, 500],
            )
        },
    )

    assert result.direction == "bullish"
    assert result.score > 0.0
    assert result.features["volume_ratio"] > 1.0


def test_volume_agent_detects_bearish_volume_expansion():
    agent = VolumeAgent()

    result = agent.observe(
        "BTC-USD",
        {
            "candles": candles(
                [105, 105, 105, 105, 105, 100],
                [100, 100, 100, 100, 100, 500],
            )
        },
    )

    assert result.direction == "bearish"
    assert result.score < 0.0


def test_volatility_agent_detects_low_volatility():
    agent = VolatilityAgent()

    result = agent.observe(
        "BTC-USD",
        {
            "candles": candles(
                [100, 100.1, 100, 100.1, 100, 100.1, 100, 100.1]
            )
        },
    )

    assert result.direction == "low_volatility"
    assert result.features["realized_volatility"] >= 0.0


def test_volatility_agent_detects_elevated_volatility():
    agent = VolatilityAgent()

    result = agent.observe(
        "BTC-USD",
        {
            "candles": candles(
                [100, 110, 95, 115, 90, 120, 85, 125]
            )
        },
    )

    assert result.direction in {
        "elevated_volatility",
        "high_volatility",
    }
    assert result.confidence > 0.25
