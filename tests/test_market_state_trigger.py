from atlas.market.trigger import MarketState, MarketStateTrigger


class FakeClock:
    def __init__(self, now=0.0):
        self.now = now

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


def build_state(**overrides):
    data = {
        "symbol": "BTCUSD",
        "price": 100.0,
        "previous_close": 99.0,
        "change_percent": 1.01,
        "trend": "Bullish",
        "volume_ratio": 1.1,
    }
    data.update(overrides)
    return MarketState(**data)


def test_market_state_trigger_first_observation_triggers_analysis():
    clock = FakeClock()
    trigger = MarketStateTrigger(clock=clock)

    assert trigger.should_analyze(build_state()) is True


def test_market_state_trigger_unchanged_state_does_not_trigger_repeated_analysis():
    clock = FakeClock()
    trigger = MarketStateTrigger(clock=clock)
    state = build_state()

    assert trigger.should_analyze(state) is True
    assert trigger.should_analyze(state) is False


def test_market_state_trigger_material_change_triggers_analysis():
    clock = FakeClock()
    trigger = MarketStateTrigger(clock=clock)
    initial = build_state(price=100.0, previous_close=99.0, change_percent=1.01)
    changed = build_state(price=110.0, previous_close=99.0, change_percent=11.11, trend="Bullish")

    assert trigger.should_analyze(initial) is True

    clock.advance(29)
    assert trigger.should_analyze(changed) is False

    clock.advance(30)
    assert trigger.should_analyze(changed) is True


def test_market_state_trigger_uses_injected_state_and_clock_for_determinism():
    clock = FakeClock(now=1000.0)
    trigger = MarketStateTrigger(
        clock=clock,
        min_change_percent=2.0,
        min_volume_ratio_delta=0.5,
        min_trigger_interval_seconds=30.0,
    )

    base = build_state(price=100.0, previous_close=99.0, change_percent=1.0, volume_ratio=1.0)
    same = build_state(price=100.0, previous_close=99.0, change_percent=1.0, volume_ratio=1.0)
    different = build_state(price=105.0, previous_close=99.0, change_percent=6.0, volume_ratio=1.7)

    assert trigger.should_analyze(base) is True
    assert trigger.should_analyze(same) is False

    clock.advance(29)
    assert trigger.should_analyze(different) is False

    clock.advance(30)
    assert trigger.should_analyze(different) is True
