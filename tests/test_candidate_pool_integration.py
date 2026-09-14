from atlas.market.candidates.source import Candidate, CandidatePool


class FakeSource:
    def __init__(self, candidates):
        self.candidates = candidates
        self.calls = 0

    def discover(self):
        self.calls += 1
        return list(self.candidates)


def test_candidate_pool_combines_market_and_ai_sources():
    market = FakeSource(
        [
            Candidate(
                symbol="AAPL",
                source="market_discovery",
                score=70,
                reason="Strong market momentum",
            ),
            Candidate(
                symbol="NVDA",
                source="market_discovery",
                score=80,
                reason="High relative strength",
            ),
        ]
    )

    ai = FakeSource(
        [
            Candidate(
                symbol="NVDA",
                source="ai_research",
                score=92,
                reason="Strong AI infrastructure thesis",
            ),
            Candidate(
                symbol="BTC-USD",
                source="ai_research",
                score=88,
                reason="Positive crypto catalyst",
            ),
        ]
    )

    pool = CandidatePool([market, ai])

    result = pool.collect()

    assert market.calls == 1
    assert ai.calls == 1
    assert [candidate.symbol for candidate in result] == [
        "NVDA",
        "BTC-USD",
        "AAPL",
    ]
    assert result[0].source == "ai_research"
    assert result[0].score == 92


def test_candidate_pool_deduplicates_using_highest_score():
    market = FakeSource(
        [
            Candidate(
                symbol="NVDA",
                source="market_discovery",
                score=80,
                reason="Market signal",
            )
        ]
    )

    ai = FakeSource(
        [
            Candidate(
                symbol="NVDA",
                source="ai_research",
                score=95,
                reason="AI research signal",
            )
        ]
    )

    result = CandidatePool([market, ai]).collect()

    assert len(result) == 1
    assert result[0].symbol == "NVDA"
    assert result[0].score == 95
    assert result[0].source == "ai_research"
    assert result[0].reason == "AI research signal"


def test_candidate_pool_is_deterministic():
    first = FakeSource(
        [
            Candidate(symbol="AAPL", source="market_discovery", score=80),
            Candidate(symbol="NVDA", source="market_discovery", score=90),
        ]
    )

    second = FakeSource(
        [
            Candidate(symbol="BTC-USD", source="ai_research", score=85),
        ]
    )

    pool = CandidatePool([first, second])

    result_one = pool.collect()
    result_two = pool.collect()

    assert result_one == result_two
