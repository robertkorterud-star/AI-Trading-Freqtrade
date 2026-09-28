from atlas.market.candidates.source import Candidate, CandidatePool


class FakeSource:
    def __init__(self, candidates):
        self.candidates = candidates
        self.calls = 0

    def discover(self):
        self.calls += 1
        return list(self.candidates)


def test_candidate_contains_research_context():
    candidate = Candidate(
        symbol="aapl",
        source="ai_research",
        score=82.5,
        reason="Strong earnings catalyst",
        metadata={"theme": "AI infrastructure"},
    )

    assert candidate.symbol == "aapl"
    assert candidate.source == "ai_research"
    assert candidate.score == 82.5
    assert candidate.reason == "Strong earnings catalyst"
    assert candidate.metadata["theme"] == "AI infrastructure"


def test_candidate_pool_normalizes_symbols():
    source = FakeSource(
        [
            Candidate(
                symbol=" aapl ",
                source="market_discovery",
                score=50,
            )
        ]
    )

    result = CandidatePool([source]).collect()

    assert result[0].symbol == "AAPL"


def test_candidate_pool_removes_empty_symbols():
    source = FakeSource(
        [
            Candidate(symbol="", source="test"),
            Candidate(symbol="   ", source="test"),
            Candidate(symbol="NVDA", source="test", score=10),
        ]
    )

    result = CandidatePool([source]).collect()

    assert [candidate.symbol for candidate in result] == ["NVDA"]


def test_candidate_pool_merges_duplicate_symbols_using_highest_score():
    market = FakeSource(
        [
            Candidate(
                symbol="AAPL",
                source="market_discovery",
                score=55,
                reason="Momentum",
            )
        ]
    )
    ai = FakeSource(
        [
            Candidate(
                symbol="AAPL",
                source="ai_research",
                score=85,
                reason="Strong AI catalyst",
            )
        ]
    )

    result = CandidatePool([market, ai]).collect()

    assert len(result) == 1
    assert result[0].symbol == "AAPL"
    assert result[0].score == 85
    assert result[0].source == "ai_research"
    assert result[0].reason == "Strong AI catalyst"


def test_candidate_pool_keeps_distinct_symbols():
    source = FakeSource(
        [
            Candidate(symbol="AAPL", source="market", score=80),
            Candidate(symbol="NVDA", source="market", score=70),
            Candidate(symbol="BTC-USD", source="market", score=60),
        ]
    )

    result = CandidatePool([source]).collect()

    assert [candidate.symbol for candidate in result] == [
        "AAPL",
        "NVDA",
        "BTC-USD",
    ]


def test_candidate_pool_sorts_by_score():
    source = FakeSource(
        [
            Candidate(symbol="AAPL", source="test", score=30),
            Candidate(symbol="NVDA", source="test", score=90),
            Candidate(symbol="MSFT", source="test", score=60),
        ]
    )

    result = CandidatePool([source]).collect()

    assert [candidate.symbol for candidate in result] == [
        "NVDA",
        "MSFT",
        "AAPL",
    ]


def test_candidate_pool_calls_each_source_once():
    first = FakeSource(
        [Candidate(symbol="AAPL", source="first", score=50)]
    )
    second = FakeSource(
        [Candidate(symbol="NVDA", source="second", score=40)]
    )

    CandidatePool([first, second]).collect()

    assert first.calls == 1
    assert second.calls == 1


def test_candidate_pool_handles_source_with_no_candidates():
    empty = FakeSource([])
    healthy = FakeSource(
        [Candidate(symbol="ETH-USD", source="healthy", score=75)]
    )

    result = CandidatePool([empty, healthy]).collect()

    assert len(result) == 1
    assert result[0].symbol == "ETH-USD"


def test_candidate_pool_does_not_mutate_source_metadata():
    metadata = {"theme": "semiconductors"}
    source = FakeSource(
        [
            Candidate(
                symbol="NVDA",
                source="ai_research",
                score=90,
                metadata=metadata,
            )
        ]
    )

    result = CandidatePool([source]).collect()

    result[0].metadata["theme"] = "changed"

    assert metadata["theme"] == "semiconductors"


def test_candidate_pool_preserves_complementary_metadata_for_duplicate_symbol():
    market = FakeSource(
        [
            Candidate(
                symbol="NVDA",
                source="market_discovery",
                score=70,
                metadata={
                    "asset_type": "stock",
                    "horizon": "day_trade",
                },
            )
        ]
    )
    ai = FakeSource(
        [
            Candidate(
                symbol="NVDA",
                source="ai_research",
                score=90,
                reason="Strong AI catalyst",
                metadata={"theme": "AI infrastructure"},
            )
        ]
    )

    result = CandidatePool([market, ai]).collect()

    assert len(result) == 1
    assert result[0].score == 90
    assert result[0].source == "ai_research"
    assert result[0].reason == "Strong AI catalyst"
    assert result[0].metadata == {
        "asset_type": "stock",
        "horizon": "day_trade",
        "theme": "AI infrastructure",
    }

def test_research_ticker_source_creates_candidates_from_related_tickers():
    from atlas.market.candidates.research_tickers import ResearchTickerSource

    articles = (
        {
            "title": "Chip demand accelerates",
            "related_tickers": [
                {
                    "symbol": "AMD",
                    "relevance_score": 0.91,
                    "sentiment_score": 0.42,
                    "sentiment": "positive",
                },
                {
                    "symbol": "NVDA",
                    "relevance_score": 0.84,
                    "sentiment_score": 0.31,
                    "sentiment": "positive",
                },
            ],
        },
    )

    candidates = ResearchTickerSource(articles).discover()

    assert [candidate.symbol for candidate in candidates] == [
        "AMD",
        "NVDA",
    ]
    assert candidates[0].source == "research_ticker"
    assert candidates[0].score == 91.0
    assert candidates[0].metadata["relevance_score"] == 0.91
    assert candidates[0].metadata["sentiment"] == "positive"

