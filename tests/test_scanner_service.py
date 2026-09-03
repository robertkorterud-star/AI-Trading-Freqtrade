from atlas.market.market_scout import AssetType, MarketObservation
from atlas.services.scanner_service import ScannerService


def observation(symbol: str, change: float, volume: float = 500_000.0) -> MarketObservation:
    return MarketObservation(
        symbol=symbol,
        asset_type=AssetType.STOCK,
        price=10.0,
        volume=volume,
        average_volume=100_000.0,
        change_percent=change,
        relative_volume_5m=2.0,
    )


def test_scanner_service_returns_ranked_candidates() -> None:
    service = ScannerService()
    result = service.scan([
        observation("LOW", 2.0),
        observation("HIGH", 15.0),
    ])

    assert result.scanned == 2
    assert result.eligible == 2
    assert [item.symbol for item in result.candidates] == ["HIGH", "LOW"]


def test_scanner_service_counts_filtered_observations() -> None:
    service = ScannerService()
    result = service.scan([
        observation("VALID", 5.0),
        observation("THIN", 5.0, volume=50_000.0),
    ])

    assert result.scanned == 2
    assert result.eligible == 1
    assert [item.symbol for item in result.candidates] == ["VALID"]


def test_scanner_service_serializes_explainable_evidence() -> None:
    service = ScannerService()
    result = service.scan([observation("AAPL", 12.0)])

    payload = service.as_dict(result)

    assert payload["scanned"] == 1
    assert payload["eligible"] == 1
    candidate = payload["candidates"][0]
    assert candidate["symbol"] == "AAPL"
    assert candidate["asset_type"] == "stock"
    assert candidate["score"] > 0
    assert "strong daily momentum" in candidate["reasons"]
