from atlas.market.candidates.ai_provider import AICandidateProvider


class FakeAI:
    def __init__(self, response):
        self.response = response
        self.prompts = []

    def discover_candidates(self, research):
        self.prompts.append(research)
        return self.response


def test_ai_candidate_provider_returns_candidates():
    ai = FakeAI(
        [
            {
                "symbol": "nvda",
                "score": 91,
                "reason": "Strong catalyst and momentum.",
            },
            {
                "symbol": "BTC-USD",
                "score": 84,
                "reason": "Positive crypto catalyst.",
            },
        ]
    )

    provider = AICandidateProvider(ai)

    candidates = provider.discover_candidates(
        "NVDA reported strong results. BTC has improving sentiment."
    )

    assert [candidate.symbol for candidate in candidates] == [
        "NVDA",
        "BTC-USD",
    ]
    assert candidates[0].source == "ai_research"
    assert candidates[0].score == 91
    assert candidates[0].reason == "Strong catalyst and momentum."


def test_ai_candidate_provider_clamps_invalid_scores():
    ai = FakeAI(
        [
            {"symbol": "AAPL", "score": 150},
            {"symbol": "AMD", "score": -20},
        ]
    )

    candidates = AICandidateProvider(ai).discover_candidates()

    assert candidates[0].score == 100
    assert candidates[1].score == 0


def test_ai_candidate_provider_ignores_invalid_items():
    ai = FakeAI(
        [
            {"symbol": "", "score": 90},
            "invalid",
            {"symbol": "MSFT", "score": 80},
        ]
    )

    candidates = AICandidateProvider(ai).discover_candidates()

    assert len(candidates) == 1
    assert candidates[0].symbol == "MSFT"


def test_ai_candidate_provider_accepts_json_response():
    ai = FakeAI(
        '[{"symbol":"TSLA","score":77,"reason":"Catalyst"}]'
    )

    candidates = AICandidateProvider(ai).discover_candidates()

    assert len(candidates) == 1
    assert candidates[0].symbol == "TSLA"


def test_ai_candidate_provider_rejects_unsupported_provider():
    class UnsupportedAI:
        pass

    provider = AICandidateProvider(UnsupportedAI())

    try:
        provider.discover_candidates()
    except TypeError as exc:
        assert "does not support candidate research" in str(exc)
    else:
        raise AssertionError("Expected TypeError")


def test_ai_candidate_provider_builds_research_prompt():
    ai = FakeAI([])

    AICandidateProvider(ai).discover_candidates(
        "Market research input"
    )

    assert len(ai.prompts) == 1
    assert "Market research input" in ai.prompts[0]
    assert "Market research input" in ai.prompts[0]
