from atlas.trading.indicator_engine import (
    IndicatorEngine,
)
from atlas.trading.market_analysis_snapshot import (
    MarketAnalysisSnapshot,
)
from atlas.trading.market_regime import (
    MarketRegimeAnalyzer,
)
from atlas.trading.multi_timeframe_analysis import (
    MultiTimeframeAnalyzer,
)


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


def _mtf_data():
    return {
        timeframe: {
            "trend": "BULLISH",
            "momentum": "POSITIVE",
            "data_available": True,
            "data_quality": "GOOD",
        }
        for timeframe in (
            "4h",
            "1h",
            "15m",
            "5m",
            "1m",
        )
    }


def test_market_analysis_snapshot_combines_analysis():
    indicators = IndicatorEngine().calculate(
        _candles()
    )

    regime = MarketRegimeAnalyzer().analyze(
        indicators
    )

    multi_timeframe = MultiTimeframeAnalyzer().analyze(
        "XRP-USD",
        _mtf_data(),
    )

    snapshot = MarketAnalysisSnapshot(
        symbol="XRP-USD",
        indicators=indicators,
        regime=regime,
        multi_timeframe=multi_timeframe,
    )

    assert snapshot.symbol == "XRP-USD"
    assert snapshot.overall_signal == "BUY"
    assert snapshot.confidence > 0
    assert snapshot.alignment == 100.0
    assert snapshot.regime_name == regime.regime


def test_market_analysis_snapshot_exposes_data_quality():
    indicators = IndicatorEngine().calculate(
        _candles()
    )

    regime = MarketRegimeAnalyzer().analyze(
        indicators
    )

    multi_timeframe = MultiTimeframeAnalyzer().analyze(
        "XRP-USD",
        _mtf_data(),
    )

    snapshot = MarketAnalysisSnapshot(
        symbol="XRP-USD",
        indicators=indicators,
        regime=regime,
        multi_timeframe=multi_timeframe,
    )

    assert snapshot.data_quality == "GOOD"


def test_market_analysis_snapshot_detects_missing_indicator_data():
    indicators = IndicatorEngine().calculate([])

    regime = MarketRegimeAnalyzer().analyze(
        indicators
    )

    multi_timeframe = MultiTimeframeAnalyzer().analyze(
        "XRP-USD",
        {},
    )

    snapshot = MarketAnalysisSnapshot(
        symbol="XRP-USD",
        indicators=indicators,
        regime=regime,
        multi_timeframe=multi_timeframe,
    )

    assert snapshot.data_quality == "MISSING"
    assert snapshot.overall_signal == "WAIT"
