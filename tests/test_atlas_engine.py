from atlas.core.engine import AtlasEngine
from atlas.trading.trading_runtime import TradingRuntime


def test_atlas_engine_uses_btc_usd_symbol():

    engine = AtlasEngine()

    results = engine.analysis_service.analyze("BTC-USD")

    assert results
    assert all(
        result.symbol == "BTC-USD"
        for result in results
    )


def test_atlas_engine_has_trading_runtime():

    engine = AtlasEngine()

    assert isinstance(
        engine.trading_runtime,
        TradingRuntime,
    )
