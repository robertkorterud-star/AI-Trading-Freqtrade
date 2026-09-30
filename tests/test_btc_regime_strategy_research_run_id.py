import pytest

from datetime import datetime, timezone

from atlas.trading.run_btc_regime_strategy_research import (
    build_research_run_id,
)


def test_same_actual_research_period_has_same_run_id():
    start = datetime(
        2026, 1, 1, 0, 0,
        tzinfo=timezone.utc,
    )
    end = datetime(
        2026, 1, 31, 0, 0,
        tzinfo=timezone.utc,
    )

    first = build_research_run_id(
        symbol="BTC-USD",
        start=start,
        end=end,
    )
    second = build_research_run_id(
        symbol="BTC-USD",
        start=start,
        end=end,
    )

    assert first == second


def test_different_actual_research_period_has_different_run_id():
    first = build_research_run_id(
        symbol="BTC-USD",
        start=datetime(
            2026, 1, 1,
            tzinfo=timezone.utc,
        ),
        end=datetime(
            2026, 1, 31,
            tzinfo=timezone.utc,
        ),
    )

    second = build_research_run_id(
        symbol="BTC-USD",
        start=datetime(
            2026, 2, 1,
            tzinfo=timezone.utc,
        ),
        end=datetime(
            2026, 2, 28,
            tzinfo=timezone.utc,
        ),
    )

    assert first != second


def test_research_periods_are_chronological_and_non_overlapping():
    from datetime import timedelta

    from atlas.trading.historical_market_data import (
        HistoricalMarketData,
        OHLCVBar,
    )
    from atlas.trading.run_btc_regime_strategy_research import (
        split_research_periods,
    )

    start = datetime(
        2026, 1, 1,
        tzinfo=timezone.utc,
    )

    bars = []

    for index in range(100):
        price = 100.0 + index

        bars.append(
            OHLCVBar(
                timestamp=start + timedelta(hours=index),
                open=price,
                high=price + 1.0,
                low=price - 1.0,
                close=price,
                volume=1.0,
            )
        )

    data = HistoricalMarketData(
        symbol="BTC-USD",
        timeframe="1h",
        source="test",
        bars=bars,
    )

    periods = split_research_periods(
        data,
        period_size=20,
    )

    assert len(periods) == 5
    assert [len(period) for period in periods] == [
        20, 20, 20, 20, 20,
    ]

    assert periods[0].bars == tuple(bars[0:20])
    assert periods[1].bars == tuple(bars[20:40])
    assert periods[2].bars == tuple(bars[40:60])
    assert periods[3].bars == tuple(bars[60:80])
    assert periods[4].bars == tuple(bars[80:100])

    for previous, current in zip(
        periods,
        periods[1:],
    ):
        assert previous.end < current.start

    for period in periods:
        assert period.symbol == data.symbol
        assert period.timeframe == data.timeframe
        assert period.source == data.source


def test_each_research_period_is_backtested_and_remembered_separately():
    from datetime import timedelta

    from atlas.trading.historical_market_data import (
        HistoricalMarketData,
        OHLCVBar,
    )
    from atlas.trading.regime_strategy_backtest import (
        RegimeStrategyBacktestSummary,
    )
    from atlas.trading.run_btc_regime_strategy_research import (
        research_periods,
    )

    start = datetime(
        2026, 1, 1,
        tzinfo=timezone.utc,
    )

    bars = []

    for index in range(60):
        price = 100.0 + index

        bars.append(
            OHLCVBar(
                timestamp=start + timedelta(hours=index),
                open=price,
                high=price + 1.0,
                low=price - 1.0,
                close=price,
                volume=1.0,
            )
        )

    data = HistoricalMarketData(
        symbol="BTC-USD",
        timeframe="1h",
        source="test",
        bars=bars,
    )

    class FakeResearch:
        def __init__(self):
            self.periods = []

        def run(self, period):
            self.periods.append(period)

            return RegimeStrategyBacktestSummary(
                results=()
            )

    class FakeMemoryService:
        def __init__(self):
            self.calls = []

        def remember(
            self,
            *,
            symbol,
            summary,
            research_run_id=None,
        ):
            self.calls.append(
                (
                    symbol,
                    summary,
                    research_run_id,
                )
            )

    research = FakeResearch()
    memory_service = FakeMemoryService()

    summaries = research_periods(
        data=data,
        period_size=20,
        research=research,
        memory_service=memory_service,
    )

    assert len(summaries) == 3
    assert len(research.periods) == 3
    assert len(memory_service.calls) == 3

    expected_periods = [
        tuple(bars[0:20]),
        tuple(bars[20:40]),
        tuple(bars[40:60]),
    ]

    assert [
        period.bars
        for period in research.periods
    ] == expected_periods

    run_ids = [
        call[2]
        for call in memory_service.calls
    ]

    assert len(set(run_ids)) == 3

    for index, call in enumerate(
        memory_service.calls
    ):
        symbol, summary, run_id = call
        period = research.periods[index]

        assert symbol == "BTC-USD"
        assert summary is summaries[index]
        assert run_id == build_research_run_id(
            symbol="BTC-USD",
            start=period.start,
            end=period.end,
        )


def test_research_periods_use_warmup_but_identify_only_evaluation_period():
    from datetime import timedelta

    from atlas.trading.historical_market_data import (
        HistoricalMarketData,
        OHLCVBar,
    )
    from atlas.trading.regime_strategy_backtest import (
        RegimeStrategyBacktestSummary,
    )
    from atlas.trading.run_btc_regime_strategy_research import (
        research_periods,
    )

    start = datetime(
        2026, 1, 1,
        tzinfo=timezone.utc,
    )

    bars = []

    for index in range(50):
        price = 100.0 + index

        bars.append(
            OHLCVBar(
                timestamp=start + timedelta(hours=index),
                open=price,
                high=price + 1.0,
                low=price - 1.0,
                close=price,
                volume=1.0,
            )
        )

    data = HistoricalMarketData(
        symbol="BTC-USD",
        timeframe="1h",
        source="test",
        bars=bars,
    )

    class FakeResearch:
        def __init__(self):
            self.calls = []

        def run(
            self,
            period,
            *,
            evaluation_start_index=0,
        ):
            self.calls.append(
                (
                    period,
                    evaluation_start_index,
                )
            )

            return RegimeStrategyBacktestSummary(
                results=()
            )

    class FakeMemoryService:
        def __init__(self):
            self.calls = []

        def remember(
            self,
            *,
            symbol,
            summary,
            research_run_id=None,
        ):
            self.calls.append(
                (
                    symbol,
                    summary,
                    research_run_id,
                )
            )

    research = FakeResearch()
    memory_service = FakeMemoryService()

    summaries = research_periods(
        data=data,
        period_size=10,
        warmup_size=20,
        research=research,
        memory_service=memory_service,
    )

    assert len(summaries) == 3
    assert len(research.calls) == 3
    assert len(memory_service.calls) == 3

    expected_bars = [
        tuple(bars[0:30]),
        tuple(bars[10:40]),
        tuple(bars[20:50]),
    ]

    for index, (
        period,
        evaluation_start_index,
    ) in enumerate(research.calls):
        assert period.bars == expected_bars[index]
        assert evaluation_start_index == 20

    evaluation_ranges = [
        (bars[20].timestamp, bars[29].timestamp),
        (bars[30].timestamp, bars[39].timestamp),
        (bars[40].timestamp, bars[49].timestamp),
    ]

    run_ids = [
        call[2]
        for call in memory_service.calls
    ]

    assert run_ids == [
        build_research_run_id(
            symbol="BTC-USD",
            start=evaluation_start,
            end=evaluation_end,
        )
        for evaluation_start, evaluation_end
        in evaluation_ranges
    ]

    assert len(set(run_ids)) == 3


def test_research_periods_reject_invalid_sizes():
    from datetime import timedelta

    from atlas.trading.run_btc_regime_strategy_research import (
        research_periods,
    )
    from atlas.trading.historical_market_data import (
        HistoricalMarketData,
        OHLCVBar,
    )

    start = datetime(
        2026, 1, 1,
        tzinfo=timezone.utc,
    )

    bars = [
        OHLCVBar(
            timestamp=start + timedelta(hours=index),
            open=100.0,
            high=101.0,
            low=99.0,
            close=100.0,
            volume=1.0,
        )
        for index in range(10)
    ]

    data = HistoricalMarketData(
        symbol="BTC-USD",
        timeframe="1h",
        source="test",
        bars=bars,
    )

    class Unused:
        pass

    with pytest.raises(
        ValueError,
        match="period_size",
    ):
        research_periods(
            data=data,
            period_size=0,
            research=Unused(),
            memory_service=Unused(),
        )

    with pytest.raises(
        ValueError,
        match="warmup_size",
    ):
        research_periods(
            data=data,
            period_size=5,
            warmup_size=-1,
            research=Unused(),
            memory_service=Unused(),
        )
