from types import SimpleNamespace

from atlas.core.engine import AtlasEngine
from atlas.market.candidates.source import Candidate


class FakeAIProvider:
    def discover_candidates(self, prompt):
        return [
            {
                "symbol": "AMD",
                "score": 92,
                "reason": "Strong AI catalyst",
            },
            {
                "symbol": "BTC-USD",
                "score": 84,
                "reason": "Improving crypto momentum",
            },
        ]


class FakeDiscovery:
    def discover(self, universe, limit=None):
        return [
            SimpleNamespace(symbol="NVDA", score=80),
            SimpleNamespace(symbol="AMD", score=70),
        ]


def test_engine_research_candidates_combines_ai_and_market(
    monkeypatch,
):
    engine = object.__new__(AtlasEngine)

    engine.config = SimpleNamespace(
        ai_provider="openai",
        language="en",
    )
    engine.asset_discovery = FakeDiscovery()
    engine.asset_universe = object()

    monkeypatch.setattr(
        "atlas.core.engine.AIProviderFactory.create",
        lambda config: FakeAIProvider(),
    )

    candidates = engine.research_candidates(
        research="AI semiconductor demand is increasing.",
        limit=10,
    )

    assert [candidate.symbol for candidate in candidates] == [
        "AMD",
        "BTC-USD",
        "NVDA",
    ]

    assert candidates[0].source == "ai_research"
    assert candidates[0].score == 92


def test_engine_research_candidates_respects_limit(
    monkeypatch,
):
    engine = object.__new__(AtlasEngine)

    engine.config = SimpleNamespace(
        ai_provider="openai",
        language="en",
    )
    engine.asset_discovery = FakeDiscovery()
    engine.asset_universe = object()

    monkeypatch.setattr(
        "atlas.core.engine.AIProviderFactory.create",
        lambda config: FakeAIProvider(),
    )

    candidates = engine.research_candidates(
        limit=2,
    )

    assert len(candidates) == 2


def test_engine_research_candidates_does_not_modify_universe(
    monkeypatch,
):
    engine = object.__new__(AtlasEngine)

    engine.config = SimpleNamespace(
        ai_provider="openai",
        language="en",
    )
    engine.asset_discovery = FakeDiscovery()

    universe = SimpleNamespace()
    engine.asset_universe = universe

    monkeypatch.setattr(
        "atlas.core.engine.AIProviderFactory.create",
        lambda config: FakeAIProvider(),
    )

    engine.research_candidates()

    assert engine.asset_universe is universe


def test_engine_research_candidates_passes_research_to_ai(
    monkeypatch,
):
    engine = object.__new__(AtlasEngine)

    engine.config = SimpleNamespace(
        ai_provider="openai",
        language="en",
    )
    engine.asset_discovery = FakeDiscovery()
    engine.asset_universe = object()

    captured = {}

    class CapturingAI:
        def discover_candidates(self, research):
            captured["research"] = research
            return []

    monkeypatch.setattr(
        "atlas.core.engine.AIProviderFactory.create",
        lambda config: CapturingAI(),
    )

    engine.research_candidates(
        research="Breaking news about semiconductor demand.",
    )

    assert captured["research"] == (
        "Breaking news about semiconductor demand."
    )
