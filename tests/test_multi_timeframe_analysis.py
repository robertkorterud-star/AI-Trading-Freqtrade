from atlas.trading.multi_timeframe_analysis import (
    MultiTimeframeAnalyzer,
)


def test_multi_timeframe_confirms_buy():

    data = {
        "4h": {
            "trend": "BULLISH",
            "momentum": "POSITIVE",
        },
        "1h": {
            "trend": "BULLISH",
            "momentum": "POSITIVE",
        },
        "15m": {
            "trend": "BULLISH",
            "momentum": "POSITIVE",
        },
        "5m": {
            "trend": "BULLISH",
            "momentum": "POSITIVE",
        },
        "1m": {
            "trend": "BULLISH",
            "momentum": "POSITIVE",
        },
    }

    result = MultiTimeframeAnalyzer().analyze(
        "XRP-USD",
        data,
    )

    assert result.overall_signal == "BUY"
    assert result.confidence == 90.0
    assert result.alignment == 100.0
    assert len(result.timeframes) == 5


def test_multi_timeframe_waits_for_confirmation():

    data = {
        "4h": {
            "trend": "BULLISH",
            "momentum": "POSITIVE",
        },
        "1h": {
            "trend": "BULLISH",
            "momentum": "POSITIVE",
        },
        "15m": {
            "trend": "BEARISH",
            "momentum": "NEGATIVE",
        },
        "5m": {
            "trend": "BEARISH",
            "momentum": "NEGATIVE",
        },
        "1m": {
            "trend": "NEUTRAL",
            "momentum": "NEUTRAL",
        },
    }

    result = MultiTimeframeAnalyzer().analyze(
        "XRP-USD",
        data,
    )

    assert result.overall_signal == "WAIT"


def test_multi_timeframe_handles_missing_timeframes():

    data = {
        "4h": {
            "trend": "BULLISH",
            "momentum": "POSITIVE",
        },
        "1h": {
            "trend": "BULLISH",
            "momentum": "POSITIVE",
        },
    }

    result = MultiTimeframeAnalyzer().analyze(
        "XRP-USD",
        data,
    )

    assert result.overall_signal == "WAIT"
    assert len(result.timeframes) == 2


def test_multi_timeframe_quality_reflects_missing_expected_timeframes():

    data = {
        "4h": {
            "trend": "BULLISH",
            "momentum": "POSITIVE",
            "data_quality": "GOOD",
        },
        "1h": {
            "trend": "BULLISH",
            "momentum": "POSITIVE",
            "data_quality": "GOOD",
        },
    }

    result = MultiTimeframeAnalyzer().analyze(
        "XRP-USD",
        data,
    )

    assert result.data_quality == "PARTIAL"
