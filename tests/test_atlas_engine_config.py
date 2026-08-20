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


def test_atlas_config_defaults_to_ollama_ai_provider():
    from atlas.core.config import AtlasConfig

    config = AtlasConfig()

    assert config.ai_provider == "ollama"


def test_atlas_config_supports_ollama_ai_provider():
    from atlas.core.config import AtlasConfig

    config = AtlasConfig(
        ai_provider="ollama",
    )

    assert config.ai_provider == "ollama"
