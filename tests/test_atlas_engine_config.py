from atlas.core.config import AtlasConfig
from atlas.core.engine import AtlasEngine


def test_atlas_engine_accepts_paper_config():

    config = AtlasConfig(
        trading_mode="paper",
        paper_trading=True,
    )

    engine = AtlasEngine(config=config)

    assert engine.config.trading_mode == "paper"
    assert engine.config.paper_trading is True
