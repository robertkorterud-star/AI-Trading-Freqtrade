#!/usr/bin/env python3
"""Smoke-check live Yahoo Finance market data through ATLAS."""

import sys

from atlas.adapters.market_data import MarketDataAdapter, oslo_symbol


def main() -> int:
    symbols = sys.argv[1:] or ["TRMED", "HPUR", "TECH", "NOD", "QEC"]
    market = MarketDataAdapter()

    for raw_symbol in symbols:
        symbol = oslo_symbol(raw_symbol)
        try:
            data = market.get(symbol)
        except Exception as exc:  # noqa: BLE001 - diagnostic script
            print(f"{symbol}: ERROR: {exc}")
            continue

        print(
            f"{symbol}: price={data.price:.4f} {data.currency} "
            f"change={data.change_percent:+.2f}% "
            f"MA20={data.ma20:.4f} MA50={data.ma50:.4f} "
            f"volume={data.volume:.0f} volume_ratio={data.volume_ratio:.2f}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
