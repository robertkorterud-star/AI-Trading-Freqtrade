from types import SimpleNamespace

import atlas.dashboard.app as dashboard_app


def test_strategy_research_cache_miss_runs_research_once(monkeypatch):
    calls = []
    result = SimpleNamespace(
        symbol="XRP-USD",
        strategies=[],
        backtests=[],
        assessments=[],
    )

    class FakeResearch:
        def research(self, symbol, research):
            calls.append((symbol, research))
            return result

    dashboard_app._strategy_research_cache.clear()
    monkeypatch.setattr(
        dashboard_app,
        "strategy_research",
        FakeResearch(),
    )

    research_items = [{"title": "test"}]

    first = dashboard_app.get_cached_strategy_research(
        "XRP-USD",
        research_items,
    )
    second = dashboard_app.get_cached_strategy_research(
        "XRP-USD",
        research_items,
    )

    assert first is result
    assert second is result
    assert calls == [("XRP-USD", research_items)]


def test_strategy_research_cache_researches_after_ttl(monkeypatch):
    calls = []
    results = [
        SimpleNamespace(symbol="XRP-USD", strategies=[]),
        SimpleNamespace(symbol="XRP-USD", strategies=[]),
    ]
    now = [100.0]

    class FakeResearch:
        def research(self, symbol, research):
            calls.append((symbol, research))
            return results.pop(0)

    dashboard_app._strategy_research_cache.clear()
    monkeypatch.setattr(
        dashboard_app,
        "strategy_research",
        FakeResearch(),
    )
    monkeypatch.setattr(
        dashboard_app.time,
        "monotonic",
        lambda: now[0],
    )

    research_items = [{"title": "test"}]

    first = dashboard_app.get_cached_strategy_research(
        "XRP-USD",
        research_items,
    )

    now[0] += dashboard_app.STRATEGY_RESEARCH_CACHE_TTL + 0.1

    second = dashboard_app.get_cached_strategy_research(
        "XRP-USD",
        research_items,
    )

    assert first is not second
    assert len(calls) == 2


def test_strategy_research_api_uses_cache(monkeypatch):
    calls = []
    result = SimpleNamespace(
        symbol="XRP-USD",
        strategies=[],
        backtests=[],
    )

    class FakeResearch:
        def research(self, symbol, research):
            calls.append((symbol, research))
            return result

    class FakeIntelligence:
        def get(self, symbol):
            return [{"title": "test"}]

    dashboard_app._strategy_research_cache.clear()
    dashboard_app._intelligence_sources_cache.clear()
    monkeypatch.setattr(
        dashboard_app,
        "strategy_research",
        FakeResearch(),
    )
    monkeypatch.setattr(
        dashboard_app,
        "intelligence_sources",
        FakeIntelligence(),
    )

    class Request:
        query_params = {"symbol": "XRP-USD"}

    first = __import__(
        "asyncio"
    ).run(
        dashboard_app.strategy_research_api(Request())
    )
    second = __import__(
        "asyncio"
    ).run(
        dashboard_app.strategy_research_api(Request())
    )

    assert first.body == second.body
    assert len(calls) == 1
