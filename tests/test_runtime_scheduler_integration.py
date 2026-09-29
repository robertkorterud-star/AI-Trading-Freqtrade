from types import SimpleNamespace

from atlas.core.runtime_loop import AtlasRuntimeLoop
from atlas.market.candidates.research_scheduler import CandidateResearchScheduler
from atlas.market.trigger import MarketState


class FakeResearchService:
    def __init__(self):
        self.calls = 0

    def get_context(self, limit=50):
        self.calls += 1
        return SimpleNamespace()


class FakeLogger:
    def __init__(self):
        self.messages = []

    def info(self, message):
        self.messages.append(message)


class FakeAssetUniverse:
    def all(self):
        return [SimpleNamespace(symbol="AAPL")]

    def count(self):
        return len(self.all())


class FakeTechnicalService:
    def __init__(self):
        self.snapshot = SimpleNamespace(
            symbol="AAPL",
            price=100.0,
            previous_close=99.0,
            change_percent=1.01,
            trend="Bullish",
            volume_ratio=1.5,
        )

    def get_snapshot(self, symbol):
        assert symbol == "AAPL"
        return self.snapshot


class FakeEngine:
    def __init__(self):
        self.candidate_research_service = FakeResearchService()
        self.logger = FakeLogger()
        self.asset_universe = FakeAssetUniverse()
        self.technical = FakeTechnicalService()
        self.starts = 0

    def research_candidates(self):
        return []

    def expand_universe_from_candidates(self, candidates):
        return 0

    def start(self, trigger_symbol=None):
        self.starts += 1


def test_runtime_once_refreshes_research_and_triggers_canonical_engine_cycle():
    engine = FakeEngine()
    scheduler = CandidateResearchScheduler(
        service=engine.candidate_research_service,
        research_interval_seconds=600,
    )
    loop = AtlasRuntimeLoop(
        engine=engine,
        interval_seconds=30,
        research_scheduler=scheduler,
    )

    triggered = loop.run_once()

    assert triggered is True
    assert engine.starts == 1
    assert engine.candidate_research_service.calls == 1
    assert engine.logger.messages == [
        "ATLAS candidate research context refreshed.",
        "ATLAS research candidates: ; added=0; active_universe=1",
    ]


def test_runtime_keeps_market_trigger_state_per_symbol():
    engine = FakeEngine()
    engine.asset_universe.all = lambda: [
        SimpleNamespace(symbol="AAPL"),
        SimpleNamespace(symbol="MSFT"),
    ]
    msft_snapshot = SimpleNamespace(
        symbol="MSFT",
        price=200.0,
        previous_close=199.0,
        change_percent=0.5,
        trend="Neutral",
        volume_ratio=1.0,
    )

    def get_snapshot(symbol):
        if symbol == "MSFT":
            return msft_snapshot
        return engine.technical.snapshot

    engine.technical.get_snapshot = get_snapshot

    loop = AtlasRuntimeLoop(
        engine=engine,
        interval_seconds=30,
        research_scheduler=CandidateResearchScheduler(
            service=engine.candidate_research_service,
        ),
    )

    assert loop.run_once() is True
    assert set(loop._market_state_triggers) == {"AAPL", "MSFT"}
    assert engine.starts == 1


def test_market_state_is_the_runtime_trigger_input():
    state = MarketState(
        symbol="AAPL",
        price=100.0,
        previous_close=99.0,
        change_percent=1.01,
        trend="Bullish",
        volume_ratio=1.5,
    )

    assert state.symbol == "AAPL"
    assert state.percent_move == 1.01


def test_runtime_forwards_trigger_symbol_to_canonical_engine_cycle():
    class TriggerAwareEngine(FakeEngine):
        def __init__(self):
            super().__init__()
            self.trigger_symbols = []

        def start(self, trigger_symbol=None):
            self.starts += 1
            self.trigger_symbols.append(trigger_symbol)

    engine = TriggerAwareEngine()

    loop = AtlasRuntimeLoop(
        engine=engine,
        interval_seconds=30,
        research_scheduler=CandidateResearchScheduler(
            service=engine.candidate_research_service,
        ),
    )

    assert loop.run_once() is True
    assert engine.starts == 1
    assert engine.trigger_symbols == ["AAPL"]


def test_runtime_observes_all_market_states_before_starting_engine_cycle():
    class MultiAssetUniverse:
        def all(self):
            return [
                SimpleNamespace(symbol="AAPL"),
                SimpleNamespace(symbol="MSFT"),
                SimpleNamespace(symbol="NVDA"),
            ]

        def count(self):
            return 3

    class MultiAssetTechnicalService:
        def get_snapshot(self, symbol):
            prices = {
                "AAPL": 100.0,
                "MSFT": 200.0,
                "NVDA": 300.0,
            }
            return SimpleNamespace(
                symbol=symbol,
                price=prices[symbol],
                previous_close=prices[symbol] - 1.0,
                change_percent=1.01,
                trend="Bullish",
                volume_ratio=1.5,
            )

    engine = FakeEngine()
    engine.asset_universe = MultiAssetUniverse()
    engine.technical = MultiAssetTechnicalService()

    trigger_symbols = []

    def start(trigger_symbol=None):
        engine.starts += 1
        trigger_symbols.append(trigger_symbol)

    engine.start = start

    loop = AtlasRuntimeLoop(
        engine=engine,
        interval_seconds=30,
        research_scheduler=CandidateResearchScheduler(
            service=engine.candidate_research_service,
        ),
    )

    assert loop.run_once() is True

    # The first eligible symbol owns this cycle, but every symbol must have
    # established its lightweight trigger baseline during the same scan.
    assert trigger_symbols == ["AAPL"]
    assert set(loop._market_state_triggers) == {
        "AAPL",
        "MSFT",
        "NVDA",
    }

    # Unchanged states must not cause the remaining first-observation
    # triggers to start expensive engine cycles on subsequent runtime passes.
    assert loop.run_once() is False
    assert trigger_symbols == ["AAPL"]
