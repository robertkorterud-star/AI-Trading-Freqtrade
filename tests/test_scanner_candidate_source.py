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
