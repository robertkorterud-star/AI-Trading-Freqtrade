from atlas.market.candidates.ai_research import AIResearchSource
from atlas.market.candidates.source import Candidate


class FakeAIResearchProvider:
    def __init__(self, candidates):
        self.candidates = candidates
        self.calls = 0

    def discover_candidates(self):
        self.calls += 1
        return list(self.candidates)


def test_ai_research_source_uses_provider():
    provider = FakeAIResearchProvider(
        [
            Candidate(
                symbol="NVDA",
                source="ai_research",
                score=91,
                reason="Strong AI infrastructure thesis",
            )
        ]
    )

    source = AIResearchSource(provider)

    result = source.discover()

    assert provider.calls == 1
    assert len(result) == 1
    assert result[0].symbol == "NVDA"
    assert result[0].source == "ai_research"
    assert result[0].score == 91
    assert result[0].reason == "Strong AI infrastructure thesis"


def test_ai_research_source_filters_empty_symbols():
    provider = FakeAIResearchProvider(
        [
            Candidate(symbol="", source="ai_research", score=90),
            Candidate(symbol="   ", source="ai_research", score=80),
            Candidate(symbol="BTC-USD", source="ai_research", score=75),
        ]
    )

    result = AIResearchSource(provider).discover()

    assert len(result) == 1
    assert result[0].symbol == "BTC-USD"


def test_ai_research_source_preserves_provider_order():
    provider = FakeAIResearchProvider(
        [
            Candidate(symbol="NVDA", source="ai_research", score=90),
            Candidate(symbol="AAPL", source="ai_research", score=80),
            Candidate(symbol="BTC-USD", source="ai_research", score=70),
        ]
    )

    result = AIResearchSource(provider).discover()

    assert [candidate.symbol for candidate in result] == [
        "NVDA",
        "AAPL",
        "BTC-USD",
    ]


def test_ai_research_source_handles_no_candidates():
    provider = FakeAIResearchProvider([])

    result = AIResearchSource(provider).discover()

    assert result == []
    assert provider.calls == 1
