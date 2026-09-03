"""
ATLAS Dashboard
"""

import time

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from atlas.i18n.translations import translate
from atlas.dashboard.dashboard_service import DashboardService
from atlas.services.settings_service import SettingsService
from atlas.services.market_search_service import MarketSearchService
from atlas.services.adaptive_strategy_research_service import (
    AdaptiveStrategyResearchService,
)
from atlas.adapters.intelligence_sources import (
    IntelligenceSourceAdapter,
)
from atlas.adapters.web_research import (
    WebResearchAdapter,
)
from atlas.adapters.binance_market_data import BinanceMarketDataAdapter
from atlas.adapters.historical_market_data import (
    HistoricalMarketDataAdapter,
)
from atlas.services.multi_timeframe_service import (
    MultiTimeframeService,
)

app = FastAPI(title="ATLAS Dashboard")

app.mount(
    "/static",
    StaticFiles(directory="atlas/dashboard/static"),
    name="static",
)

templates = Jinja2Templates(
    directory="atlas/dashboard/templates"
)


def get_language():
    return settings_service.get_language()


def template_translate(key):
    return translate(get_language(), key)


templates.env.globals["t"] = template_translate
templates.env.globals["get_language"] = get_language

service = DashboardService()
settings_service = service.data.settings
market_search = MarketSearchService()
historical_market_data = HistoricalMarketDataAdapter()
binance_market_data = BinanceMarketDataAdapter()

web_research = WebResearchAdapter()

strategy_research = AdaptiveStrategyResearchService(
    web_research=web_research,
)

multi_timeframe_service = MultiTimeframeService()

intelligence_sources = IntelligenceSourceAdapter(
    web=web_research,
)


STRATEGY_RESEARCH_CACHE_TTL = 300.0

_strategy_research_cache = {}
_intelligence_sources_cache = {}

MULTI_TIMEFRAME_CACHE_TTL = 30.0
_multi_timeframe_cache = {}


def get_cached_intelligence_sources(symbol: str):
    """Return cached web research for a symbol."""
    now = time.monotonic()
    cached = _intelligence_sources_cache.get(symbol)
    if cached is not None:
        created_at, result = cached
        if now - created_at < STRATEGY_RESEARCH_CACHE_TTL:
            return result
    result = intelligence_sources.get(symbol)
    _intelligence_sources_cache[symbol] = (now, result)
    return result


def get_cached_strategy_research(symbol: str, research_items: list[dict]):
    """Return cached strategy research for a symbol while it is fresh."""
    now = time.monotonic()
    cached = _strategy_research_cache.get(symbol)
    if cached is not None:
        created_at, result = cached
        if now - created_at < STRATEGY_RESEARCH_CACHE_TTL:
            return result
    result = strategy_research.research(
        symbol=symbol,
        research=research_items,
    )
    _strategy_research_cache[symbol] = (now, result)
    return result


def get_cached_multi_timeframe(symbol: str):
    """Return a short-lived multi-timeframe analysis."""
    now = time.monotonic()
    cached = _multi_timeframe_cache.get(symbol)
    if cached is not None:
        created_at, result = cached
        if now - created_at < MULTI_TIMEFRAME_CACHE_TTL:
            return result
    result = multi_timeframe_service.analyze(symbol)
    _multi_timeframe_cache[symbol] = (now, result)
    return result


def summarize_research_sources(items: list[dict]):
    """Summarize research channels and publishers."""
    channels = {}
    publishers = {}
    for item in items or []:
        channel = str(item.get("source", "Unknown")).strip() or "Unknown"
        channels[channel] = channels.get(channel, 0) + 1
        publisher = str(item.get("publisher", "")).strip()
        if publisher:
            publishers[publisher] = publishers.get(publisher, 0) + 1
    return {
        "channels": sorted(channels.items(), key=lambda item: (-item[1], item[0].lower())),
        "publishers": sorted(publishers.items(), key=lambda item: (-item[1], item[0].lower())),
    }


def build_dashboard(selected_symbol=None):
    return service.get_dashboard(selected_symbol=selected_symbol)


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    selected_symbol = request.query_params.get("symbol")
    dashboard = build_dashboard(selected_symbol=selected_symbol)
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"request": request, "dashboard": dashboard},
    )


@app.get("/scanner", response_class=HTMLResponse)
async def scanner(request: Request):
    """ATLAS Scanner page; uses only the hourly scanner snapshot."""
    dashboard = {"scanner": service.get_scanner()}
    return templates.TemplateResponse(
        request=request,
        name="scanner.html",
        context={"request": request, "dashboard": dashboard},
    )


@app.get("/api/dashboard")
async def dashboard_api(request: Request):
    selected_symbol = request.query_params.get("symbol")
    dashboard = build_dashboard(selected_symbol=selected_symbol)
    return JSONResponse(
        content={
            "status": dashboard["status"],
            "version": dashboard["version"],
            "currency": dashboard["currency"],
            "technical": dashboard["technical"],
            "intelligence": dashboard["intelligence"],
            "decision": {
                "action": dashboard["decision"].action.value if dashboard["decision"] else None,
                "confidence": dashboard["decision"].confidence if dashboard["decision"] else None,
                "evidence": dashboard["decision"].evidence if dashboard["decision"] else None,
            },
            "market": dashboard["market"],
            "news": [
                {
                    "title": article.title,
                    "source": article.source,
                    "summary": article.summary,
                    "url": article.url,
                    "sentiment": article.sentiment,
                }
                for article in dashboard["news"]
            ],
        }
    )


@app.get("/analysis", response_class=HTMLResponse)
async def analysis(request: Request, symbol: str | None = None):
    dashboard = service.get_dashboard(selected_symbol=symbol)
    return templates.TemplateResponse(
        request=request,
        name="analysis.html",
        context={"request": request, "dashboard": dashboard},
    )


@app.get("/api/market-search")
async def market_search_api(request: Request):
    query = request.query_params.get("q", "").strip()
    if not query:
        return JSONResponse(content={"results": []})
    results = market_search.search(query)
    return JSONResponse(
        content={
            "results": [
                {
                    "symbol": item["symbol"],
                    "name": item["name"],
                    "type": item["type"],
                    "market": item.get("market"),
                    "currency": item.get("currency"),
                    "price_usd": item.get("price_usd"),
                    "change": item.get("change"),
                }
                for item in results
            ]
        }
    )


@app.get("/market/{symbol}", response_class=HTMLResponse)
async def market_terminal(request: Request, symbol: str):
    normalized = symbol.strip().upper()
    results = market_search.search(normalized)
    asset = next((item for item in results if item.get("symbol", "").upper() == normalized), None)
    if asset is None:
        return RedirectResponse(url="/markets?q=" + normalized, status_code=302)
    trading_status = settings_service.get_trading_status()
    dashboard = {"status": "ATLAS Online", "trading": trading_status}
    return templates.TemplateResponse(
        request=request,
        name="market_terminal.html",
        context={"request": request, "asset": asset, "dashboard": dashboard},
    )


@app.get("/api/fx-rate")
async def fx_rate_api(request: Request):
    source = request.query_params.get("source", "USD").strip().upper()
    target = request.query_params.get("target", "NOK").strip().upper()
    supported = {"USD", "NOK", "DKK", "SEK", "EUR"}
    if source not in supported or target not in supported:
        return JSONResponse(content={"error": "Unsupported currency."}, status_code=400)
    if source == target:
        return JSONResponse(content={"source": source, "target": target, "rate": 1.0})

    def usd_per_currency(currency: str) -> float:
        if currency == "USD":
            return 1.0
        rates = {"NOK": 10.0, "DKK": 6.5, "SEK": 9.5, "EUR": 0.92}
        return rates[currency]

    rate = usd_per_currency(target) / usd_per_currency(source)
    return JSONResponse(content={"source": source, "target": target, "rate": rate})
