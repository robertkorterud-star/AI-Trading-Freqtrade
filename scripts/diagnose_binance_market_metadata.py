"""Read-only diagnostic comparing Binance Spot market metadata.

Run from the repository root:

    python -u scripts/diagnose_binance_market_metadata.py

No assets are persisted and no trading cycle is started.
"""

from __future__ import annotations

from pprint import pprint

from atlas.adapters.binance import BinanceAdapter


SYMBOLS = (
    "BTCUSDT",
    "ETHUSDT",
    "SANDUSDT",
    "AAPLBUSDT",
    "AMZNBUSDT",
    "PLTRBUSDT",
    "SQQQBUSDT",
)


def main() -> None:
    adapter = BinanceAdapter()
    exchange_info = adapter.get_exchange_info()
    markets = {
        str(item.get("symbol", "")).upper(): item
        for item in exchange_info.get("symbols", [])
        if isinstance(item, dict)
    }

    print("Read-only Binance exchangeInfo metadata comparison")
    print(f"Exchange markets returned: {len(markets)}")

    for symbol in SYMBOLS:
        print(f"\n========== {symbol} ==========")
        market = markets.get(symbol)
        if market is None:
            print("NOT PRESENT")
            continue
        pprint(market, sort_dicts=True)


if __name__ == "__main__":
    main()
