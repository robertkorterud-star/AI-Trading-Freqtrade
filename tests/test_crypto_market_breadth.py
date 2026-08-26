from atlas.trading.crypto_market_breadth import (
    CryptoMarketBreadthAnalyzer,
)
from atlas.trading.crypto_market_context import (
    CryptoAssetContext,
)


def _asset(
    symbol,
    change,
    volume=1000,
):
    return CryptoAssetContext(
        coin_id=symbol.lower(),
        symbol=symbol,
        name=symbol,
        price=100.0,
        market_cap=1000000.0,
        market_cap_rank=None,
        volume_24h=volume,
        change_24h=change,
        change_7d=None,
        change_30d=None,
        circulating_supply=None,
        total_supply=None,
        data_quality="GOOD",
    )


def test_breadth_detects_broad_bullish_market():
    assets = [
        _asset("BTC", 5.0),
        _asset("ETH", 4.0),
        _asset("SOL", 3.0),
        _asset("XRP", 2.0),
        _asset("ADA", 1.0),
        _asset("DOGE", -1.0),
        _asset("AVAX", 2.0),
        _asset("LINK", 3.0),
        _asset("DOT", 1.0),
        _asset("UNI", 2.0),
    ]

    result = CryptoMarketBreadthAnalyzer().analyze(
        assets
    )

    assert result.total_assets == 10
    assert result.advancing_assets == 9
    assert result.declining_assets == 1
    assert result.unchanged_assets == 0

    assert result.advance_ratio == 0.9
    assert result.decline_ratio == 0.1

    assert result.average_change_24h == 2.2
    assert result.median_change_24h == 2.0

    assert result.breadth_regime == "BROAD_BULLISH"
    assert result.data_quality == "GOOD"


def test_breadth_detects_broad_bearish_market():
    assets = [
        _asset("BTC", -5.0),
        _asset("ETH", -4.0),
        _asset("SOL", -3.0),
        _asset("XRP", -2.0),
        _asset("ADA", -1.0),
        _asset("DOGE", 1.0),
        _asset("AVAX", -2.0),
        _asset("LINK", -3.0),
        _asset("DOT", -1.0),
        _asset("UNI", -2.0),
    ]

    result = CryptoMarketBreadthAnalyzer().analyze(
        assets
    )

    assert result.advancing_assets == 1
    assert result.declining_assets == 9
    assert result.breadth_regime == "BROAD_BEARISH"


def test_breadth_detects_mixed_market():
    assets = [
        _asset("BTC", 2.0),
        _asset("ETH", -2.0),
        _asset("SOL", 1.0),
        _asset("XRP", -1.0),
    ]

    result = CryptoMarketBreadthAnalyzer().analyze(
        assets
    )

    assert result.total_assets == 4
    assert result.advancing_assets == 2
    assert result.declining_assets == 2
    assert result.breadth_regime == "MIXED"


def test_breadth_handles_missing_data():
    result = CryptoMarketBreadthAnalyzer().analyze(
        []
    )

    assert result.total_assets == 0
    assert result.advance_ratio == 0.0
    assert result.decline_ratio == 0.0
    assert result.average_change_24h is None
    assert result.median_change_24h is None
    assert result.breadth_regime == "UNKNOWN"
    assert result.data_quality == "MISSING"


def test_breadth_handles_partial_data():
    assets = [
        _asset("BTC", 5.0),
        _asset("ETH", None),
        _asset("SOL", None),
        _asset("XRP", -2.0),
        _asset("ADA", None),
    ]

    result = CryptoMarketBreadthAnalyzer().analyze(
        assets
    )

    assert result.total_assets == 5
    assert result.advancing_assets == 1
    assert result.declining_assets == 1
    assert result.data_quality == "POOR"


def test_breadth_counts_volume_participation():
    assets = [
        _asset("BTC", 5.0),
        _asset("ETH", 3.0),
        _asset("SOL", -2.0),
        _asset("XRP", -1.0),
    ]

    result = CryptoMarketBreadthAnalyzer().analyze(
        assets
    )

    assert result.volume_up_assets == 2
    assert result.volume_down_assets == 2
