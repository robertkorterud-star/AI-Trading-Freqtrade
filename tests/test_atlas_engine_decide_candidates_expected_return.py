from types import SimpleNamespace

from atlas.core.config import AtlasConfig
from atlas.core.engine import AtlasEngine
from atlas.models.action import Action
from atlas.models.analysis_result import AnalysisResult


class StubAnalysisService:
    def __init__(self, results):
        self.results = results

    def analyze(self, symbol):
        return list(self.results)


class StubAssetDiscovery:
    def discover(self, universe):
        return [SimpleNamespace(symbol="BTC-USD", score=1.0)]


class StubCandidateSelector:
    def select(self, discovered, limit=3, minimum_score=0.0):
        return list(discovered)[:limit]


class StubMarketData:
    def get_snapshot(self, symbol):
        return SimpleNamespace(price=100.0, regime=None)


def _buy_analysis():
    return [
        AnalysisResult(
            symbol="BTC-USD",
            analyst="test",
            action=Action.BUY,
            confidence=90.0,
            evidence=90.0,
            reasoning=["test signal"],
        )
    ]


def test_atlas_engine_decide_candidates_carries_expected_return():
    engine = AtlasEngine(
        config=AtlasConfig(
            trading_mode="paper",
            paper_trading=True,
        )
    )

    engine.asset_discovery = StubAssetDiscovery()
    engine.candidate_selector = StubCandidateSelector()
    engine.market_data = StubMarketData()
    engine.analysis_service = StubAnalysisService(_buy_analysis())

    class StubExpectedReturnService:
        def estimate(self, symbol, action):
            assert symbol == "BTC-USD"
            assert action == Action.BUY
            return 0.0125

    engine.expected_return_service = StubExpectedReturnService()
    engine.decision_engine.expected_return_service = engine.expected_return_service

    decisions = engine.decide_candidates(limit=1)

    assert len(decisions) == 1
    decision = decisions[0]["decision"]
    assert decision.action == Action.BUY
    assert decision.expected_return == 0.0125


def test_atlas_engine_decide_candidates_without_expected_return_service_preserves_zero():
    engine = AtlasEngine(
        config=AtlasConfig(
            trading_mode="paper",
            paper_trading=True,
        )
    )

    engine.asset_discovery = StubAssetDiscovery()
    engine.candidate_selector = StubCandidateSelector()
    engine.market_data = StubMarketData()
    engine.analysis_service = StubAnalysisService(_buy_analysis())
    engine.expected_return_service = None
    engine.decision_engine.expected_return_service = None

    decisions = engine.decide_candidates(limit=1)

    assert len(decisions) == 1
    decision = decisions[0]["decision"]
    assert decision.action == Action.BUY
    assert decision.expected_return == 0.0

def test_atlas_engine_decide_candidates_carries_expected_return_availability():
    engine = AtlasEngine(
        config=AtlasConfig(
            trading_mode="paper",
            paper_trading=True,
        )
    )

    engine.asset_discovery = StubAssetDiscovery()
    engine.candidate_selector = StubCandidateSelector()
    engine.market_data = StubMarketData()
    engine.analysis_service = StubAnalysisService(_buy_analysis())

    class StubEstimate:
        value = 0.0
        ready = True

    class StubExpectedReturnService:
        def estimate(self, symbol, action):
            assert symbol == "BTC-USD"
            assert action == Action.BUY
            return 0.0

        def estimate_with_status(self, symbol, action):
            assert symbol == "BTC-USD"
            assert action == Action.BUY
            return StubEstimate()

    engine.expected_return_service = StubExpectedReturnService()
    engine.decision_engine.expected_return_service = engine.expected_return_service

    decisions = engine.decide_candidates(limit=1)

    decision = decisions[0]["decision"]
    assert decision.expected_return == 0.0
    assert decision.expected_return_ready is True

