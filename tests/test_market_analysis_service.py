from atlas.services.market_analysis_service import (
    MarketAnalysisService,
)


class FakeMarketData:
    pass


class FakeMultiTimeframeService:

    def analyze(self, symbol):
        return {
            "4h": {
                "trend": "BULLISH",
                "momentum": "POSITIVE",
                "data_available": True,
                "data_quality": "GOOD",
            },
            "1h": {
                "trend": "BULLISH",
                "momentum": "POSITIVE",
                "data_available": True,
                "data_quality": "GOOD",
            },
            "15m": {
                "trend": "BULLISH",
                "momentum": "POSITIVE",
                "data_available": True,
                "data_quality": "GOOD",
            },
            "5m": {
                "trend": "BULLISH",
                "momentum": "POSITIVE",
                "data_available": True,
                "data_quality": "GOOD",
            },
            "1m": {
                "trend": "NEUTRAL",
                "momentum": "NEUTRAL",
                "data_available": True,
                "data_quality": "GOOD",
            },
        }


def _candles(
    start=100.0,
    step=0.5,
    count=250,
):
    result = []

    for index in range(count):
        close = start + index * step

        result.append(
            {
                "timestamp": str(index),
                "open": close - 0.1,
                "high": close + 0.2,
                "low": close - 0.2,
                "close": close,
                "volume": 1000,
            }
        )

    return result


def test_market_analysis_service_builds_snapshot():

    service = MarketAnalysisService(
        market_data=FakeMarketData(),
        multi_timeframe_service=(
            FakeMultiTimeframeService()
        ),
    )

    snapshot = service.analyze(
        "XRP-USD",
        _candles(),
    )

    assert snapshot.symbol == "XRP-USD"
    assert snapshot.indicators.data_quality == "GOOD"

    assert snapshot.regime.regime in {
        "BREAKOUT_UP",
        "TRENDING_UP",
        "RANGING",
        "HIGH_VOLATILITY",
        "LOW_VOLATILITY",
    }

    assert snapshot.multi_timeframe.overall_signal == "BUY"
    assert snapshot.confidence > 0
    assert snapshot.alignment > 0


def test_market_analysis_service_handles_missing_candles():

    service = MarketAnalysisService(
        market_data=FakeMarketData(),
        multi_timeframe_service=(
            FakeMultiTimeframeService()
        ),
    )

    snapshot = service.analyze(
        "XRP-USD",
        [],
    )

    assert snapshot.indicators.data_quality == "MISSING"
    assert snapshot.regime.regime == "UNKNOWN"
    assert snapshot.multi_timeframe.overall_signal == "WAIT"
    assert snapshot.multi_timeframe.confidence == 0.0
    assert snapshot.multi_timeframe.alignment == 0.0
