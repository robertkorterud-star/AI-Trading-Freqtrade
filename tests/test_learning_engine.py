from atlas.learning import (
    LearningEngine,
    PerformanceAttribution,
    TradeOutcome,
)


def outcome(
    trade_id: str,
    pnl: float,
    agent: str | None = None,
    regime: str | None = None,
    horizon: str | None = None,
    signal: str | None = None,
) -> TradeOutcome:
    return TradeOutcome(
        trade_id=trade_id,
        symbol="BTC-USD",
        side="long",
        entry_price=100.0,
        exit_price=110.0 if pnl > 0 else 90.0,
        quantity=1.0,
        pnl=pnl,
        return_pct=pnl,
        holding_period=10.0,
        agent=agent,
        regime=regime,
        horizon=horizon,
        signal=signal,
        confidence=0.8,
        risk_score=0.2,
    )


def test_trade_outcome_identifies_wins():
    assert outcome("1", 10.0).is_win
    assert not outcome("2", -5.0).is_win


def test_overall_performance():
    attribution = PerformanceAttribution()

    attribution.record(outcome("1", 10.0))
    attribution.record(outcome("2", -4.0))
    attribution.record(outcome("3", 6.0))

    stats = attribution.overall()

    assert stats.trades == 3
    assert stats.wins == 2
    assert stats.losses == 1
    assert stats.win_rate == 2 / 3
    assert stats.total_pnl == 12.0
    assert stats.expectancy == 4.0


def test_agent_attribution():
    attribution = PerformanceAttribution()

    attribution.record(outcome("1", 10.0, agent="momentum"))
    attribution.record(outcome("2", -2.0, agent="momentum"))
    attribution.record(outcome("3", 8.0, agent="news"))

    report = attribution.by_agent()

    assert report["momentum"].trades == 2
    assert report["momentum"].total_pnl == 8.0
    assert report["news"].total_pnl == 8.0


def test_regime_attribution():
    attribution = PerformanceAttribution()

    attribution.record(outcome("1", 10.0, regime="bull"))
    attribution.record(outcome("2", -5.0, regime="bear"))
    attribution.record(outcome("3", 6.0, regime="bull"))

    report = attribution.by_regime()

    assert report["bull"].trades == 2
    assert report["bull"].total_pnl == 16.0
    assert report["bear"].total_pnl == -5.0


def test_horizon_and_signal_attribution():
    attribution = PerformanceAttribution()

    attribution.record(
        outcome(
            "1",
            10.0,
            horizon="swing",
            signal="buy",
        )
    )

    attribution.record(
        outcome(
            "2",
            -2.0,
            horizon="day",
            signal="sell",
        )
    )

    assert attribution.by_horizon()["swing"].trades == 1
    assert attribution.by_signal()["buy"].total_pnl == 10.0


def test_best_agent():
    attribution = PerformanceAttribution()

    attribution.record(outcome("1", 5.0, agent="momentum"))
    attribution.record(outcome("2", 2.0, agent="news"))
    attribution.record(outcome("3", 8.0, agent="momentum"))

    assert attribution.best_agent() == "momentum"


def test_best_regime():
    attribution = PerformanceAttribution()

    attribution.record(outcome("1", 5.0, regime="bull"))
    attribution.record(outcome("2", -3.0, regime="bear"))
    attribution.record(outcome("3", 7.0, regime="bull"))

    assert attribution.best_regime() == "bull"


def test_minimum_trade_filter():
    attribution = PerformanceAttribution()

    attribution.record(outcome("1", 100.0, agent="rare"))
    attribution.record(outcome("2", 5.0, agent="stable"))
    attribution.record(outcome("3", 5.0, agent="stable"))

    assert attribution.best_agent(minimum_trades=2) == "stable"


def test_learning_engine_facade():
    engine = LearningEngine()

    engine.record_trade(
        outcome(
            "1",
            10.0,
            agent="momentum",
            regime="bull",
            horizon="swing",
            signal="buy",
        )
    )

    assert engine.summary().trades == 1
    assert engine.agent_report()["momentum"].wins == 1
    assert engine.regime_report()["bull"].total_pnl == 10.0
    assert engine.horizon_report()["swing"].trades == 1
    assert engine.signal_report()["buy"].trades == 1
