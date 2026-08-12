from atlas.core.config import AtlasConfig


def test_atlas_config_supports_explicit_paper_mode():

    config = AtlasConfig(
        trading_mode="paper",
        paper_trading=True,
    )

    assert config.trading_mode == "paper"
    assert config.paper_trading is True
