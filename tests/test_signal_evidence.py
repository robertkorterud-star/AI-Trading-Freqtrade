from atlas.trading.indicator_engine import (
    IndicatorEngine,
)
from atlas.trading.multi_timeframe_analysis import (
    MultiTimeframeAnalyzer,
)
from atlas.trading.signal_evidence import (
    SignalEvidenceAnalyzer,
)


def _candles(
    start=100.0,
    step=1.0,
    count=250,
):
    candles = []

    for index in range(count):

        if index < count - 40:
            close = start + (
                index * 0.2
            )
        else:
            acceleration = (
                index - (count - 40)
            )

            close = (
                start
                + ((count - 40) * 0.2)
                + (acceleration * 2.0)
            )

        candles.append(
            {
                "open": close - 0.5,
                "high": close + 1.0,
                "low": close - 1.0,
                "close": close,
                "volume": 1000.0,
            }
        )

    return candles


def _mtf():
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

    return MultiTimeframeAnalyzer().analyze(
        "BTC-USD",
        data,
    )


def test_signal_evidence_extracts_bullish_structure():

    indicators = IndicatorEngine().calculate(
        _candles()
    )

    multi_timeframe = _mtf()

    result = SignalEvidenceAnalyzer().analyze(
        indicators,
        multi_timeframe,
    )

    assert result.trend == "BULLISH"
    assert result.momentum == "POSITIVE"

    assert result.rsi_signal in {
        "BULLISH",
        "OVERBOUGHT",
    }

    assert result.macd_signal == "BULLISH"

    assert result.multi_timeframe_signal == "BUY"

    assert result.evidence_quality == "GOOD"


def test_signal_evidence_detects_breakout():

    candles = _candles(
        start=100,
        step=0.1,
        count=100,
    )

    candles[-1]["close"] = 200.0
    candles[-1]["high"] = 200.2

    indicators = IndicatorEngine().calculate(
        candles
    )

    multi_timeframe = _mtf()

    result = SignalEvidenceAnalyzer().analyze(
        indicators,
        multi_timeframe,
    )

    assert result.breakout in {
        "BREAKOUT_20",
        "BREAKOUT_50",
    }


def test_signal_evidence_handles_missing_data():

    indicators = IndicatorEngine().calculate(
        []
    )

    multi_timeframe = (
        MultiTimeframeAnalyzer().analyze(
            "BTC-USD",
            {},
        )
    )

    result = SignalEvidenceAnalyzer().analyze(
        indicators,
        multi_timeframe,
    )

    assert result.trend == "NEUTRAL"
    assert result.momentum == "UNKNOWN"
    assert result.volatility == "UNKNOWN"
    assert result.volume == "UNKNOWN"
    assert result.breakout == "NONE"

    assert result.rsi_signal == "UNKNOWN"
    assert result.macd_signal == "UNKNOWN"
    assert result.bollinger_signal == "UNKNOWN"
    assert result.adx_signal == "UNKNOWN"

    assert result.evidence_quality == "MISSING"


def test_signal_evidence_does_not_generate_trade_signal():

    indicators = IndicatorEngine().calculate(
        _candles()
    )

    multi_timeframe = _mtf()

    result = SignalEvidenceAnalyzer().analyze(
        indicators,
        multi_timeframe,
    )

    assert not hasattr(
        result,
        "buy",
    )

    assert not hasattr(
        result,
        "sell",
    )

    assert not hasattr(
        result,
        "decision",
    )
