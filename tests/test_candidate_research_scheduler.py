from atlas.market.candidates.research_context import CandidateResearchContext
from atlas.market.candidates.research_scheduler import CandidateResearchScheduler


class FakeClock:
    def __init__(self, now=0.0):
        self.now = now

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


class FakeResearchService:
    def __init__(self, context=None):
        self.context = context or CandidateResearchContext(
            articles=(
                {
                    "source": "Test",
                    "published_at": "2026-09-14T10:00:00",
                    "title": "Test Article",
                    "summary": "Test Summary",
                },
            )
        )
        self.calls = 0

    def get_context(self, limit=50):
        self.calls += 1
        return self.context


class FailingResearchService:
    def get_context(self, limit=50):
        raise RuntimeError("Research failed")


def test_candidate_research_scheduler_first_call_returns_true():
    clock = FakeClock()
    scheduler = CandidateResearchScheduler(clock=clock)

    assert scheduler.should_research() is True


def test_candidate_research_scheduler_before_interval_returns_false():
    clock = FakeClock()
    service = FakeResearchService()
    scheduler = CandidateResearchScheduler(
        service=service,
        clock=clock,
        research_interval_seconds=600,
    )

    scheduler.research()
    clock.advance(599)

    assert scheduler.should_research() is False


def test_candidate_research_scheduler_after_interval_returns_true():
    clock = FakeClock()
    service = FakeResearchService()
    scheduler = CandidateResearchScheduler(
        service=service,
        clock=clock,
        research_interval_seconds=600,
    )

    scheduler.research()
    clock.advance(600)

    assert scheduler.should_research() is True


def test_candidate_research_scheduler_should_research_does_not_update_timestamp():
    clock = FakeClock()
    service = FakeResearchService()
    scheduler = CandidateResearchScheduler(
        service=service,
        clock=clock,
        research_interval_seconds=600,
    )

    scheduler.research()
    clock.advance(100)
    scheduler.should_research()
    clock.advance(500)

    assert scheduler.should_research() is True


def test_candidate_research_scheduler_successful_research_registers_timestamp():
    clock = FakeClock()
    service = FakeResearchService()
    scheduler = CandidateResearchScheduler(
        service=service,
        clock=clock,
    )

    context = scheduler.research()

    assert context is not None
    assert service.calls == 1
    clock.advance(600)
    assert scheduler.should_research() is True


def test_candidate_research_scheduler_failed_research_does_not_register_timestamp():
    clock = FakeClock()
    failing_service = FailingResearchService()
    scheduler = CandidateResearchScheduler(
        service=failing_service,
        clock=clock,
        research_interval_seconds=600,
    )

    result = scheduler.research()

    assert result is None
    assert scheduler.should_research() is True


def test_candidate_research_scheduler_uses_injected_clock():
    clock = FakeClock(now=1000.0)
    service = FakeResearchService()
    scheduler = CandidateResearchScheduler(
        service=service,
        clock=clock,
        research_interval_seconds=100,
    )

    scheduler.research()
    clock.advance(99)
    assert scheduler.should_research() is False
    clock.advance(1)
    assert scheduler.should_research() is True


def test_candidate_research_scheduler_no_external_calls_at_init():
    class CountingService:
        def __init__(self):
            self.calls = 0

        def get_context(self, limit=50):
            self.calls += 1
            return CandidateResearchContext(articles=())

    service = CountingService()
    scheduler = CandidateResearchScheduler(service=service)

    assert service.calls == 0
