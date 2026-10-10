from types import SimpleNamespace

from atlas.core.engine import AtlasEngine
from atlas.market.asset import Asset
from atlas.market.asset_type import AssetType
from atlas.market.asset_universe import AssetUniverse
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


def test_engine_research_candidates_forwards_horizon_to_market_discovery(monkeypatch):
    from atlas.market.trading_horizon import TradingHorizon

    engine = object.__new__(AtlasEngine)
    engine.config = SimpleNamespace(
        ai_provider="openai",
        language="en",
    )
    engine.asset_universe = object()
    engine.candidate_research_service = FakeResearchService()

    class HorizonDiscovery:
        def __init__(self):
            self.received_horizon = None

        def discover(self, universe, limit=None, horizon=None):
            self.received_horizon = horizon
            return []

    discovery = HorizonDiscovery()
    engine.asset_discovery = discovery

    monkeypatch.setattr(
        "atlas.core.engine.AIProviderFactory.create",
        lambda config: FakeAIProvider(),
    )

    engine.research_candidates(
        research="Explicit research.",
        limit=5,
        horizon=TradingHorizon.SWING,
    )

    assert discovery.received_horizon == TradingHorizon.SWING

def test_engine_can_expand_universe_from_researched_candidate():
    engine = object.__new__(AtlasEngine)
    engine.asset_universe = AssetUniverse(assets=[])

    class FakeDynamicAssetService:
        def resolve_and_add_symbol(self, query):
            assert query == "AMD"
            return engine.asset_universe.add(
                Asset(
                    symbol="AMD",
                    name="AMD",
                    asset_type=AssetType.STOCK,
                    market="US",
                    currency="USD",
                )
            )

    engine.dynamic_asset_service = FakeDynamicAssetService()
    candidates = [
        Candidate(
            symbol="AMD",
            source="ai_research",
            score=92,
            reason="research",
        )
    ]

    added = engine.expand_universe_from_candidates(candidates)

    assert added == 1
    assert engine.asset_universe.get("AMD") is not None

def test_engine_research_candidates_includes_structured_research_tickers(
    monkeypatch,
):
    context = CandidateResearchContext(
        articles=(
            {
                "source": "Alpha Vantage",
                "title": "Cybersecurity demand expands",
                "summary": "Broad market research.",
                "related_tickers": [
                    {
                        "symbol": "PLTR",
                        "relevance_score": 0.91,
                        "sentiment_score": 0.42,
                        "sentiment": "positive",
                    }
                ],
            },
        )
    )

    engine = object.__new__(AtlasEngine)
    engine.config = SimpleNamespace(
        ai_provider="openai",
        language="en",
    )
    engine.asset_discovery = FakeDiscovery()
    engine.asset_universe = object()
    engine.candidate_research_service = FakeResearchService(
        context=context,
    )

    class EmptyAI:
        def discover_candidates(self, research):
            return []

    monkeypatch.setattr(
        "atlas.core.engine.AIProviderFactory.create",
        lambda config: EmptyAI(),
    )

    candidates = engine.research_candidates(
        research="",
        limit=10,
    )

    pltr = next(
        candidate
        for candidate in candidates
        if candidate.symbol == "PLTR"
    )

    assert pltr.source == "research_ticker"
    assert pltr.score == 91.0
    assert pltr.metadata["relevance_score"] == 0.91



def test_engine_research_candidates_includes_scanner_source(monkeypatch):
    engine = object.__new__(AtlasEngine)
    engine.config = SimpleNamespace(
        ai_provider="openai",
        language="en",
    )
    engine.asset_discovery = FakeDiscovery()
    engine.asset_universe = object()
    engine.candidate_research_service = FakeResearchService()

    class EmptyAI:
        def discover_candidates(self, research):
            return []

    class FakeScannerSource:
        def discover(self):
            return [
                Candidate(
                    symbol="QNT-USD",
                    source="etoro_scanner",
                    score=99.0,
                    reason="Scanner candidate",
                )
            ]

    engine.scanner_candidate_source = FakeScannerSource()

    monkeypatch.setattr(
        "atlas.core.engine.AIProviderFactory.create",
        lambda config: EmptyAI(),
    )

    candidates = engine.research_candidates(
        research="Explicit research.",
        limit=10,
    )

    assert any(
        candidate.symbol == "QNT-USD"
        and candidate.source == "etoro_scanner"
        for candidate in candidates
    )


def test_engine_initializes_etoro_scanner_candidate_source(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setenv(
        "ATLAS_DATABASE_PATH",
        str(tmp_path / "atlas.db"),
    )

    engine = AtlasEngine()

    from atlas.market.candidates.scanner import ScannerCandidateSource
    from atlas.services.scanner_service import ScannerService

    assert isinstance(
        engine.scanner_candidate_source,
        ScannerCandidateSource,
    )
    assert isinstance(
        engine.scanner_candidate_source.scanner,
        ScannerService,
    )


def test_binance_candidate_without_exact_resolution_is_not_added():
    """Scanner discovery alone must not make a Binance asset available."""
    from atlas.services.dynamic_asset_service import DynamicAssetService

    engine = object.__new__(AtlasEngine)
    engine.asset_universe = AssetUniverse(assets=[])

    class FakeResolver:
        def resolve(self, query):
            assert query == "GLMR-USD"
            return [
                Asset(
                    symbol="GLMRUSDT",
                    name="Moonbeam Binance pair",
                    asset_type=AssetType.CRYPTO,
                    market="crypto",
                    currency="USDT",
                )
            ]

    engine.dynamic_asset_service = DynamicAssetService(
        resolver=FakeResolver(),
        universe=engine.asset_universe,
    )

    candidate = Candidate(
        symbol="GLMR-USD",
        source="binance_scanner",
        score=51.9,
        metadata={
            "exchange": "binance",
            "scanner_symbol": "GLMRUSDT",
            "quote_asset": "USDT",
        },
    )

    added = engine.expand_universe_from_candidates([candidate])

    assert added == 0
    assert engine.asset_universe.get("GLMR-USD") is None
    assert engine.asset_universe.get("GLMRUSDT") is None


def test_engine_can_select_binance_scanner_candidate_source(
    tmp_path,
    monkeypatch,
):
    """Explicit Binance selection must reuse the canonical candidate source."""
    from atlas.core.config import AtlasConfig
    from atlas.market.candidates.scanner import ScannerCandidateSource
    from atlas.services.binance_scanner_service import BinanceScannerService

    monkeypatch.setenv(
        "ATLAS_DATABASE_PATH",
        str(tmp_path / "atlas.db"),
    )

    config = AtlasConfig(
        scanner_exchange="binance",
        binance_api_key="test-binance-key",
    )
    engine = AtlasEngine(config=config)

    assert isinstance(
        engine.scanner_candidate_source,
        ScannerCandidateSource,
    )
    assert engine.scanner_candidate_source.exchange == "binance"
    assert isinstance(
        engine.scanner_candidate_source.scanner,
        BinanceScannerService,
    )
    assert (
        engine.scanner_candidate_source.scanner.market_data.adapter.api_key
        == "test-binance-key"
    )
