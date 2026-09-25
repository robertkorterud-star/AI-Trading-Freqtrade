from types import SimpleNamespace

from atlas.core.engine import AtlasEngine
from atlas.market.asset import Asset
from atlas.market.asset_type import AssetType
from atlas.market.candidates.source import Candidate
from atlas.market.candidates.research_context import CandidateResearchContext


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
    def __init__(self):
        self.nvda = Asset(
            symbol="NVDA",
            name="NVIDIA",
            asset_type=AssetType.STOCK,
            market="US",
            currency="USD",
        )
        self.amd = Asset(
            symbol="AMD",
            name="AMD",
            asset_type=AssetType.STOCK,
            market="US",
            currency="USD",
        )

    def discover(self, universe, limit=None):
        return [
            SimpleNamespace(
                symbol="NVDA",
                score=80,
                asset=self.nvda,
            ),
            SimpleNamespace(
                symbol="AMD",
                score=70,
                asset=self.amd,
            ),
        ]


class FakeResearchService:
    def __init__(self, context=None):
        self.context = context or CandidateResearchContext(
            articles=(
                {
                    "source": "Reuters",
                    "published_at": "2026-09-14T10:00:00",
                    "title": "Market research context",
                    "summary": "Broad market research for candidate discovery.",
                },
            )
        )
        self.calls = 0

    def get_context(self, limit=50):
        self.calls += 1
        return self.context


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
    engine.candidate_research_service = FakeResearchService()

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
    engine.candidate_research_service = FakeResearchService()

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
    engine.candidate_research_service = FakeResearchService()

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


def test_engine_research_candidates_uses_service_context_when_empty(monkeypatch):
    engine = object.__new__(AtlasEngine)
    engine.config = SimpleNamespace(ai_provider="openai", language="en")
    engine.asset_discovery = FakeDiscovery()
    engine.asset_universe = object()
    fake_service = FakeResearchService()
    engine.candidate_research_service = fake_service

    captured = {}

    class CapturingAI:
        def discover_candidates(self, research):
            captured["research"] = research
            return [{"symbol": "AMD", "score": 91, "reason": "Service context"}]

    monkeypatch.setattr(
        "atlas.core.engine.AIProviderFactory.create",
        lambda config: CapturingAI(),
    )

    engine.research_candidates(research="", limit=5)

    assert fake_service.calls == 1
    assert "Market research context" in captured["research"]


def test_engine_research_candidates_bypasses_service_for_explicit_research(monkeypatch):
    engine = object.__new__(AtlasEngine)
    engine.config = SimpleNamespace(ai_provider="openai", language="en")
    engine.asset_discovery = FakeDiscovery()
    engine.asset_universe = object()

    class FailingService:
        def get_context(self, limit=50):
            raise AssertionError("should not fetch when explicit research provided")

    engine.candidate_research_service = FailingService()

    captured = {}

    class CapturingAI:
        def discover_candidates(self, research):
            captured["research"] = research
            return [{"symbol": "AMD", "score": 95, "reason": "Explicit"}]

    monkeypatch.setattr(
        "atlas.core.engine.AIProviderFactory.create",
        lambda config: CapturingAI(),
    )

    engine.research_candidates(research="Explicit AMD analysis", limit=5)

    assert captured["research"] == "Explicit AMD analysis"


def test_engine_research_candidates_reuses_service_instance(monkeypatch):
    engine = object.__new__(AtlasEngine)
    engine.config = SimpleNamespace(ai_provider="openai", language="en")
    engine.asset_discovery = FakeDiscovery()
    engine.asset_universe = object()
    fake_service = FakeResearchService()
    engine.candidate_research_service = fake_service

    class SimpleAI:
        def discover_candidates(self, research):
            return [{"symbol": "BTC-USD", "score": 88, "reason": "Test"}]

    monkeypatch.setattr(
        "atlas.core.engine.AIProviderFactory.create",
        lambda config: SimpleAI(),
    )

    engine.research_candidates(limit=5)
    engine.research_candidates(limit=5)

    assert fake_service.calls == 2


def test_engine_research_candidates_includes_market_discovery(monkeypatch):
    engine = object.__new__(AtlasEngine)
    engine.config = SimpleNamespace(ai_provider="openai", language="en")
    engine.asset_discovery = FakeDiscovery()
    engine.asset_universe = object()
    engine.candidate_research_service = FakeResearchService()

    monkeypatch.setattr(
        "atlas.core.engine.AIProviderFactory.create",
        lambda config: FakeAIProvider(),
    )

    candidates = engine.research_candidates(research="", limit=10)

    symbols = [c.symbol for c in candidates]
    assert "NVDA" in symbols
    assert "AMD" in symbols
