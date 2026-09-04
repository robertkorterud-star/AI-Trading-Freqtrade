from dataclasses import dataclass

from atlas.adapters.market_data import (
    MarketData,
    MarketDataAdapter,
    MarketDataProvider,
    oslo_symbol,
)


def test_oslo_symbol_adds_yahoo_suffix() -> None:
    assert oslo_symbol("TRMED") == "TRMED.OL"
    assert oslo_symbol("hpUr") == "HPUR.OL"
    assert oslo_symbol("TECH.OL") == "TECH.OL"


def test_oslo_symbol_rejects_empty_symbol() -> None:
    try:
        oslo_symbol("   ")
    except ValueError as exc:
        assert "empty" in str(exc)
    else:
        raise AssertionError("expected ValueError")


@dataclass
class FakeProvider:
    snapshot: MarketData

    def get(self, symbol: str) -> MarketData:
        assert symbol == self.snapshot.symbol
        return self.snapshot


def test_adapter_delegates_to_injected_provider() -> None:
    snapshot = MarketData(
        symbol="TRMED.OL",
        price=5.50,
        previous_close=5.40,
        change_percent=1.8518,
        ma20=5.20,
        ma50=4.90,
        volume=1000.0,
        average_volume=800.0,
        volume_ratio=1.25,
        currency="NOK",
    )
    provider: MarketDataProvider = FakeProvider(snapshot)
    adapter = MarketDataAdapter(provider=provider)

    assert adapter.get("TRMED.OL") == snapshot
