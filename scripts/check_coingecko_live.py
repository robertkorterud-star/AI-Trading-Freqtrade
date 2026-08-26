import requests

from atlas.trading.coingecko_http_client import (
    CoinGeckoHTTPClient,
)
from atlas.trading.coingecko_ohlc import (
    CoinGeckoOHLCProvider,
)


class RequestsTransport:

    def get(
        self,
        url,
        *,
        params,
        timeout,
    ):
        return requests.get(
            url,
            params=params,
            timeout=timeout,
        )


client = CoinGeckoHTTPClient(
    transport=RequestsTransport(),
    timeout=15.0,
)

provider = CoinGeckoOHLCProvider(
    client=client,
    coin_ids={
        "BTC-USD": "bitcoin",
    },
)

data = provider.load(
    symbol="BTC-USD",
)

print()
print("ATLAS CoinGecko Live Check")
print("==========================")
print(f"Symbol: {data.symbol}")
print(f"Candles: {len(data.bars)}")

if data.bars:
    print(
        f"First: {data.bars[0].timestamp.isoformat()}"
    )
    print(
        f"Last:  {data.bars[-1].timestamp.isoformat()}"
    )
    print(
        f"Last close: {data.bars[-1].close}"
    )

for bar in data.bars:

    if bar.open <= 0:
        raise RuntimeError("Invalid open price.")

    if bar.high <= 0:
        raise RuntimeError("Invalid high price.")

    if bar.low <= 0:
        raise RuntimeError("Invalid low price.")

    if bar.close <= 0:
        raise RuntimeError("Invalid close price.")

    if bar.low > bar.high:
        raise RuntimeError("Invalid OHLC range.")

print("OHLC validation: OK")
print()
