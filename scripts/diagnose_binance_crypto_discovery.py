"""Live read-only diagnostic for Binance crypto discovery.

Run from the repository root:

    python -u scripts/diagnose_binance_crypto_discovery.py

No assets are persisted and no trading cycle is started.
"""

from __future__ import annotations

from time import monotonic

from atlas.adapters.binance_crypto_market_data import (
    BinanceCryptoMarketDataProvider,
)
from atlas.services.scanner_service import ScannerService


CANDIDATE_LIMIT = 100
DISPLAY_LIMIT = 40


def main() -> None:
    provider = BinanceCryptoMarketDataProvider()
    scanner = ScannerService()

    print("Starting read-only Binance Spot discovery ...", flush=True)
    started = monotonic()
    result = scanner.scan_crypto(provider, limit=CANDIDATE_LIMIT)
    elapsed = monotonic() - started

    print("\n========== BINANCE DISCOVERY ==========")
    print(f"Scanned observations : {result.scanned}")
    print(f"MarketScout eligible : {result.eligible}")
    print(f"Returned candidates  : {len(result.candidates)}")
    print(f"Elapsed seconds       : {elapsed:.2f}")
    print("=======================================")

    print(f"\nTop {min(DISPLAY_LIMIT, len(result.candidates))} candidates:")
    for number, item in enumerate(result.candidates[:DISPLAY_LIMIT], 1):
        print(
            f"{number:>3}. {item.symbol:<14} "
            f"score={item.score:>7.2f} "
            f"momentum={item.momentum_score:>6.1f} "
            f"volume={item.volume_score:>6.1f} "
            f"liquidity={item.liquidity_score:>6.1f}"
        )


if __name__ == "__main__":
    main()
