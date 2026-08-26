from atlas.services.multi_timeframe_service import (
    MultiTimeframeService,
)


def _candles(
    start=100.0,
    step=0.5,
    count=60,
):
    result = []

    for index in range(count):

        close = (
            start +
            index * step
        )

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


class FakeMarketData:

    def get(
        self,
        symbol,
        period,
        interval,
    ):
        return _candles()


def test_multi_timeframe_service_uses_all_timeframes():

    service = MultiTimeframeService(
        market_data=FakeMarketData(),
    )

    result = service.analyze(
        "XRP-USD"
    )

    assert result.symbol == "XRP-USD"
    assert len(result.timeframes) == 5

    assert [
        item.timeframe
        for item in result.timeframes
    ] == [
        "4h",
        "1h",
        "15m",
        "5m",
        "1m",
    ]


def test_multi_timeframe_service_bullish_data():

    service = MultiTimeframeService(
        market_data=FakeMarketData(),
    )

    result = service.analyze(
        "XRP-USD"
    )

    assert result.overall_signal in {
        "BUY",
        "WAIT",
    }

    assert result.confidence >= 0.0
    assert result.alignment >= 0.0

def test_multi_timeframe_service_reports_missing_data():
    class MissingMarketData:
        def get(self, symbol, period, interval):
            return []

    service = MultiTimeframeService(
        market_data=MissingMarketData(),
    )

    result = service.analyze("XRP-USD")

    assert result.overall_signal == "WAIT"
    assert result.confidence == 0.0
    assert result.alignment == 0.0
    assert result.data_quality == "MISSING"
    assert result.timeframes == []


def test_multi_timeframe_service_reports_poor_data():
    class PoorMarketData:
        def get(self, symbol, period, interval):
            return _candles(count=20)

    service = MultiTimeframeService(
        market_data=PoorMarketData(),
    )

    result = service.analyze("XRP-USD")

    assert result.data_quality == "POOR"
    assert all(
        item.data_available is True
        for item in result.timeframes
    )
    assert all(
        item.data_quality == "POOR"
        for item in result.timeframes
    )


def test_multi_timeframe_service_reports_good_data():
    class GoodMarketData:
        def get(self, symbol, period, interval):
            return _candles(count=60)

    service = MultiTimeframeService(
        market_data=GoodMarketData(),
    )

    result = service.analyze("XRP-USD")

    assert result.data_quality == "GOOD"
    assert all(
        item.data_available is True
        for item in result.timeframes
    )
    assert all(
        item.data_quality == "GOOD"
        for item in result.timeframes
    )

