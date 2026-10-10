from types import SimpleNamespace

from atlas.market.market_scout import AssetType
from atlas.market.candidates.scanner import ScannerCandidateSource
from atlas.services.scanner_service import ScannerResult


class FakeScanner:
    def scan_etoro_crypto(self, limit=100):
        assert limit == 10
        return ScannerResult(
            scanned=200,
            eligible=100,
            candidates=(
                SimpleNamespace(
                    symbol="QNT",
                    asset_type=AssetType.CRYPTO,
                    score=87.5,
                    reasons=("Strong momentum", "Narrow spread"),
                ),
                SimpleNamespace(
                    symbol="ETH",
                    asset_type=AssetType.CRYPTO,
                    score=82.0,
                    reasons=("Liquid market",),
                ),
            ),
        )


def test_etoro_scanner_candidates_use_canonical_atlas_crypto_symbols():
    source = ScannerCandidateSource(
        scanner=FakeScanner(),
        limit=10,
    )

    candidates = source.discover()

    assert [candidate.symbol for candidate in candidates] == [
        "QNT-USD",
        "ETH-USD",
    ]
    assert candidates[0].source == "etoro_scanner"
    assert candidates[0].score == 87.5
    assert candidates[0].reason == "Strong momentum; Narrow spread"
    assert candidates[0].metadata["scanner_symbol"] == "QNT"
    assert candidates[0].metadata["asset_type"] == "crypto"


def test_binance_scanner_candidate_preserves_exchange_pair_identity():
    """Binance quote pairs must not become fabricated ATLAS asset symbols."""

    class FakeBinanceScanner:
        def scan(self, limit=100):
            assert limit == 10
            return ScannerResult(
                scanned=522,
                eligible=522,
                candidates=(
                    SimpleNamespace(
                        symbol="GLMRUSDT",
                        asset_type=AssetType.CRYPTO,
                        score=51.9,
                        reasons=("Strong momentum",),
                    ),
                ),
            )

    source = ScannerCandidateSource(
        scanner=FakeBinanceScanner(),
        limit=10,
        exchange="binance",
    )

    candidates = source.discover()

    assert len(candidates) == 1
    assert candidates[0].symbol == "GLMR-USD"
    assert candidates[0].source == "binance_scanner"
    assert candidates[0].metadata["scanner_symbol"] == "GLMRUSDT"
    assert candidates[0].metadata["exchange"] == "binance"
    assert candidates[0].metadata["quote_asset"] == "USDT"


def test_etoro_spot_symbols_keep_original_identity():
    class SpotScanner:
        def scan_etoro_crypto(self, limit=100):
            return ScannerResult(
                scanned=3,
                eligible=3,
                candidates=tuple(
                    SimpleNamespace(
                        symbol=symbol,
                        asset_type=AssetType.CRYPTO,
                        score=80.0,
                        reasons=("Liquid market",),
                    )
                    for symbol in ("BTC.SPOT", "XRP.SPOT", "ETH.SPOT")
                ),
            )

    candidates = ScannerCandidateSource(scanner=SpotScanner()).discover()

    assert [candidate.symbol for candidate in candidates] == [
        "BTC-USD",
        "XRP-USD",
        "ETH-USD",
    ]
    assert [candidate.metadata["scanner_symbol"] for candidate in candidates] == [
        "BTC.SPOT",
        "XRP.SPOT",
        "ETH.SPOT",
    ]
