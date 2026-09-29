import pytest
from types import SimpleNamespace

from atlas.core.runtime_loop import AtlasRuntimeLoop, run


class FakeResearchService:
    def get_context(self, limit=50):
        return SimpleNamespace()


class FakeLogger:
    def info(self, message):
        pass


class FakeAssetUniverse:
    def all(self):
        return [SimpleNamespace(symbol="AAPL")]

    def count(self):
        return len(self.all())


class FakeTechnicalService:
    def get_snapshot(self, symbol):
        return SimpleNamespace(
            symbol=symbol,
            price=100.0,
            previous_close=99.0,
            change_percent=1.01,
            trend="Bullish",
            volume_ratio=1.5,
        )


class FakeEngine:
    def __init__(self):
        self.calls = 0
        self.candidate_research_service = FakeResearchService()
        self.logger = FakeLogger()
        self.asset_universe = FakeAssetUniverse()
        self.technical = FakeTechnicalService()

    def research_candidates(self):
        return []

    def expand_universe_from_candidates(self, candidates):
        return 0

    def start(self, trigger_symbol=None):
        self.calls += 1


def test_runtime_loop_rejects_non_positive_interval():
    with pytest.raises(ValueError, match="greater than zero"):
        AtlasRuntimeLoop(engine=FakeEngine(), interval_seconds=0)


def test_runtime_loop_runs_canonical_engine_cycle(monkeypatch):
    engine = FakeEngine()
    loop = AtlasRuntimeLoop(engine=engine, interval_seconds=30)

    sleeps = []

    def fake_sleep(seconds):
        sleeps.append(seconds)
        if engine.calls >= 1:
            raise KeyboardInterrupt

    monkeypatch.setattr("atlas.core.runtime_loop.time.sleep", fake_sleep)
    monkeypatch.setattr(
        "atlas.core.runtime_loop.time.monotonic",
        iter([0.0, 0.0, 1.0]).__next__,
    )

    with pytest.raises(KeyboardInterrupt):
        loop.run_forever()

    assert engine.calls == 1
    assert sleeps == [29.0]


def test_runtime_run_loads_persisted_settings_when_no_config_is_supplied(monkeypatch):
    captured = {}

    class FakeAtlasEngine:
        def __init__(self, config=None):
            captured["config"] = config

    class FakeRuntimeLoop:
        def __init__(self, engine=None, interval_seconds=30.0):
            captured["engine"] = engine
            captured["interval_seconds"] = interval_seconds

        def run_forever(self):
            captured["started"] = True

    monkeypatch.setattr("atlas.core.runtime_loop.AtlasEngine", FakeAtlasEngine)
    monkeypatch.setattr("atlas.core.runtime_loop.AtlasRuntimeLoop", FakeRuntimeLoop)

    run(interval_seconds=45)

    assert captured["config"].load_persisted_settings is True
    assert captured["interval_seconds"] == 45
    assert captured["started"] is True


def test_runtime_loop_main_starts_continuous_runtime(monkeypatch):
    import atlas.core.runtime_loop as runtime_loop

    captured = {}

    def fake_run():
        captured["started"] = True

    monkeypatch.setattr(runtime_loop, "run", fake_run)

    runtime_loop.main()

    assert captured["started"] is True

def test_runtime_research_expands_active_universe_before_trigger_scan():
    engine = FakeEngine()
    researched = [SimpleNamespace(symbol="AMD")]

    class FakeResearchScheduler:
        def should_research(self):
            return True

        def research(self):
            return SimpleNamespace()

    engine.research_candidates = lambda: researched
    expanded = []

    def expand_universe(candidates):
        expanded.extend(candidate.symbol for candidate in candidates)
        return len(candidates)

    engine.expand_universe_from_candidates = expand_universe

    loop = AtlasRuntimeLoop(
        engine=engine,
        interval_seconds=30,
        research_scheduler=FakeResearchScheduler(),
    )

    loop.run_once()

    assert expanded == ["AMD"]



def test_runtime_reports_research_universe_expansion():
    engine = FakeEngine()
    researched = [
        SimpleNamespace(symbol="PLTR"),
        SimpleNamespace(symbol="AMD"),
    ]

    class RecordingLogger:
        def __init__(self):
            self.messages = []

        def info(self, message):
            self.messages.append(message)

    class ExpandedUniverse:
        def all(self):
            return [
                SimpleNamespace(symbol="AAPL"),
                SimpleNamespace(symbol="PLTR"),
            ]

        def count(self):
            return 2

    class FakeResearchScheduler:
        def should_research(self):
            return True

        def research(self):
            return SimpleNamespace()

    engine.logger = RecordingLogger()
    engine.asset_universe = ExpandedUniverse()
    engine.research_candidates = lambda: researched
    engine.expand_universe_from_candidates = lambda candidates: 1

    loop = AtlasRuntimeLoop(
        engine=engine,
        interval_seconds=30,
        research_scheduler=FakeResearchScheduler(),
    )

    loop.run_once()

    assert (
        "ATLAS research candidates: PLTR, AMD; "
        "added=1; active_universe=2"
    ) in engine.logger.messages


def test_runtime_run_applies_persisted_settings_before_engine_is_created(
    monkeypatch,
    tmp_path,
):
    from atlas.core.config import AtlasConfig
    from atlas.services.settings_service import SettingsService
    import atlas.core.runtime_loop as runtime_loop

    database_path = str(tmp_path / "runtime-settings.db")

    persisted_config = AtlasConfig(
        database_path=database_path,
        load_persisted_settings=True,
    )
    settings = SettingsService(config=persisted_config)
    settings.set_trading_mode("paper")

    captured = {}

    class FakeAtlasEngine:
        def __init__(self, config=None):
            captured["config"] = config

    class FakeRuntimeLoop:
        def __init__(self, engine=None, interval_seconds=30.0):
            captured["engine"] = engine

        def run_forever(self):
            captured["started"] = True

    monkeypatch.setenv("ATLAS_DATABASE_PATH", database_path)
    monkeypatch.setattr(runtime_loop, "AtlasEngine", FakeAtlasEngine)
    monkeypatch.setattr(runtime_loop, "AtlasRuntimeLoop", FakeRuntimeLoop)

    runtime_loop.run()

    assert captured["config"].trading_mode == "paper"
    assert captured["config"].paper_trading is True
