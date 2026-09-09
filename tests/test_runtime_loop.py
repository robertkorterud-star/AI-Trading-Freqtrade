import pytest

from atlas.core.runtime_loop import AtlasRuntimeLoop


class FakeEngine:
    def __init__(self):
        self.calls = 0

    def start(self):
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
        iter([0.0, 1.0]).__next__,
    )

    with pytest.raises(KeyboardInterrupt):
        loop.run_forever()

    assert engine.calls == 1
    assert sleeps == [29.0]
