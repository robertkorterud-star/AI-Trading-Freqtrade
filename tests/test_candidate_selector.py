from atlas.market.asset import Asset
from atlas.market.asset_discovery import DiscoveryScore
from atlas.market.asset_type import AssetType
from atlas.market.candidate_selector import CandidateSelector


def make_score(symbol, score, asset_type=AssetType.STOCK):
    return DiscoveryScore(
        asset=Asset(
            symbol=symbol,
            name=symbol,
            asset_type=asset_type,
            market="US",
            currency="USD",
        ),
        score=score,
    )


def test_selector_returns_highest_scoring_candidates():

    candidates = [
        make_score("AAPL", 70.0),
        make_score("NVDA", 90.0),
        make_score("MSFT", 80.0),
    ]

    selector = CandidateSelector()

    selected = selector.select(
        candidates,
        limit=2,
    )

    assert [item.symbol for item in selected] == [
        "NVDA",
        "MSFT",
    ]


def test_selector_preserves_discovery_order_when_scores_match():

    candidates = [
        make_score("AAPL", 80.0),
        make_score("NVDA", 80.0),
        make_score("MSFT", 80.0),
    ]

    selector = CandidateSelector()

    selected = selector.select(
        candidates,
        limit=2,
    )

    assert [item.symbol for item in selected] == [
        "AAPL",
        "NVDA",
    ]


def test_selector_can_require_minimum_discovery_score():

    candidates = [
        make_score("NVDA", 90.0),
        make_score("AAPL", 70.0),
        make_score("MSFT", 40.0),
    ]

    selector = CandidateSelector()

    selected = selector.select(
        candidates,
        limit=10,
        minimum_score=60.0,
    )

    assert [item.symbol for item in selected] == [
        "NVDA",
        "AAPL",
    ]


def test_selector_returns_all_valid_candidates_when_limit_is_none():

    candidates = [
        make_score("AAPL", 70.0),
        make_score("NVDA", 90.0),
        make_score("MSFT", 80.0),
    ]

    selector = CandidateSelector()

    selected = selector.select(
        candidates,
        limit=None,
    )

    assert [item.symbol for item in selected] == [
        "NVDA",
        "MSFT",
        "AAPL",
    ]


def test_triggered_candidate_is_included_in_deep_analysis_selection():
    candidates = [
        make_score("XRP-USD", 95.0, AssetType.CRYPTO),
        make_score("ETH-USD", 90.0, AssetType.CRYPTO),
        make_score("GRML", 85.0),
        make_score("AMD", 70.0),
    ]

    selector = CandidateSelector()

    selected = selector.select(
        candidates,
        limit=3,
        trigger_symbol="AMD",
    )

    assert [item.symbol for item in selected] == [
        "XRP-USD",
        "ETH-USD",
        "AMD",
    ]


def test_engine_discovery_can_preserve_triggered_candidate(monkeypatch, tmp_path):
    from atlas.core.config import AtlasConfig
    from atlas.core.engine import AtlasEngine

    engine = AtlasEngine(
        config=AtlasConfig(
            database_path=str(tmp_path / "atlas.db"),
        )
    )

    discovered = [
        make_score("XRP-USD", 95.0, AssetType.CRYPTO),
        make_score("ETH-USD", 90.0, AssetType.CRYPTO),
        make_score("GRML", 85.0),
        make_score("AMD", 70.0),
    ]

    monkeypatch.setattr(
        engine.asset_discovery,
        "discover",
        lambda *args, **kwargs: discovered,
    )

    selected = engine.discover_candidates(
        limit=3,
        trigger_symbol="AMD",
    )

    assert [item.symbol for item in selected] == [
        "XRP-USD",
        "ETH-USD",
        "AMD",
    ]


def test_engine_decision_candidates_preserve_trigger_symbol(monkeypatch, tmp_path):
    from atlas.core.config import AtlasConfig
    from atlas.core.engine import AtlasEngine

    engine = AtlasEngine(
        config=AtlasConfig(
            database_path=str(tmp_path / "atlas.db"),
        )
    )

    captured = {}

    def fake_analyze_candidates(
        limit=3,
        minimum_score=0.0,
        horizon=None,
        trigger_symbol=None,
    ):
        captured["trigger_symbol"] = trigger_symbol
        return []

    monkeypatch.setattr(
        engine,
        "analyze_candidates",
        fake_analyze_candidates,
    )

    result = engine.decide_candidates(
        limit=3,
        trigger_symbol="AMD",
    )

    assert result == []
    assert captured["trigger_symbol"] == "AMD"


def test_engine_start_forwards_trigger_symbol_to_candidate_decisions(
    monkeypatch,
    tmp_path,
):
    from atlas.core.config import AtlasConfig
    from atlas.core.engine import AtlasEngine

    engine = AtlasEngine(
        config=AtlasConfig(
            database_path=str(tmp_path / "atlas.db"),
        )
    )

    captured = {}

    monkeypatch.setattr(
        engine.asset_universe,
        "all",
        lambda: [],
    )

    monkeypatch.setattr(
        engine.prediction_evaluator,
        "evaluate_ready",
        lambda **kwargs: [],
    )

    def fake_decide_candidates(
        limit=3,
        minimum_score=0.0,
        horizon=None,
        trigger_symbol=None,
    ):
        captured["trigger_symbol"] = trigger_symbol
        return []

    monkeypatch.setattr(
        engine,
        "decide_candidates",
        fake_decide_candidates,
    )

    result = engine.start(
        trigger_symbol="AMD",
    )

    assert captured["trigger_symbol"] == "AMD"
