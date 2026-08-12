from atlas.core.engine import AtlasEngine, build_config_from_args


def test_atlas_engine_cli_supports_paper_mode():

    config = build_config_from_args(["--paper"])

    assert config.trading_mode == "paper"
    assert config.paper_trading is True


def test_atlas_engine_cli_defaults_to_advisor_mode():

    config = build_config_from_args([])

    assert config.trading_mode == "advisor"
    assert config.paper_trading is True


def test_atlas_engine_cli_creates_paper_engine():

    config = build_config_from_args(["--paper"])
    engine = AtlasEngine(config=config)

    assert engine.config.trading_mode == "paper"
    assert engine.config.paper_trading is True
