from atlas.market.candidates.research_context import CandidateResearchContext
from atlas.market.candidates.research_service import CandidateResearchService


class FakeClock:
    def __init__(self, now=0.0):
        self.now = now

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


class FakeContextBuilder:
    def __init__(self):
        self.calls = 0

    def build(self, limit=50):
        self.calls += 1
        return CandidateResearchContext(
            articles=(
                {
                    "source": "Test",
                    "published_at": "2026-09-14T10:00:00",
                    "title": f"Headline {self.calls}",
                    "summary": f"Summary {self.calls}",
                },
            )
        )


def test_candidate_research_service_first_call_performs_research():
    clock = FakeClock()
    builder = FakeContextBuilder()
    service = CandidateResearchService(
        context_builder=builder,
        clock=clock,
    )

    context = service.research()

    assert builder.calls == 1
    assert context.articles[0]["title"] == "Headline 1"


def test_candidate_research_service_reuses_cached_context_within_interval():
    clock = FakeClock()
    builder = FakeContextBuilder()
    service = CandidateResearchService(
        context_builder=builder,
        clock=clock,
    )

    first = service.get_context()
    second = service.get_context()

    assert builder.calls == 1
    assert first is second
    assert first.articles[0]["title"] == "Headline 1"


def test_candidate_research_service_refreshes_after_interval():
    clock = FakeClock()
    builder = FakeContextBuilder()
    service = CandidateResearchService(
        context_builder=builder,
        clock=clock,
    )

    first = service.research()
    clock.advance(600)
    second = service.research()

    assert builder.calls == 2
    assert first.articles[0]["title"] == "Headline 1"
    assert second.articles[0]["title"] == "Headline 2"


def test_candidate_research_service_injected_clock_makes_timing_deterministic():
    clock = FakeClock()
    builder = FakeContextBuilder()
    service = CandidateResearchService(
        context_builder=builder,
        clock=clock,
        minimum_interval_seconds=600,
    )

    first = service.get_context()
    clock.advance(599)
    cached = service.get_context()
    clock.advance(2)
    refreshed = service.get_context()

    assert builder.calls == 2
    assert first is cached
    assert cached is not refreshed
    assert refreshed.articles[0]["title"] == "Headline 2"
