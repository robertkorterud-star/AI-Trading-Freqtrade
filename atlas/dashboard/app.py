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


def template_translate(key):
    return translate(get_language(), key)


templates.env.globals["t"] = template_translate

service = DashboardService()
settings_service = SettingsService()
market_search = MarketSearchService()
strategy_research = AdaptiveStrategyResearchService()
intelligence_sources = IntelligenceSourceAdapter()
web_research = WebResearchAdapter()
binance_market_data = BinanceMarketDataAdapter()
historical_market_data = HistoricalMarketDataAdapter()
multi_timeframe = MultiTimeframeService(
    market_data=historical_market_data,
)


def get_language():
    return settings_service.get_language()


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
    scanner_data = service.get_scanner()
    scanner_data.setdefault(
        "rules",
        {
            "stock_min_price": 1.0,
            "minimum_average_volume": 100_000.0,
            "minimum_current_volume": 100_000.0,
        },
    )
    dashboard = {"scanner": scanner_data}
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
            "market": dashboard["market"],
            "market_scan": dashboard["market_scan"],
            "scanner": dashboard["scanner"],
            "portfolio": dashboard["portfolio"],
            "trading": dashboard["trading"],
            "decision": dashboard["decision"],
            "decision_explanation": dashboard["decision_explanation"],
            "decision_robustness": dashboard["decision_robustness"],
            "decision_influence": dashboard["decision_influence"],
            "analysts": dashboard["analysts"],
            "news": dashboard["news"],
            "trade_history": dashboard["trade_history"],
            "agent_performance": dashboard["agent_performance"],
        }
    )


@app.get("/api/market-search")
async def market_search_api(request: Request):
    query = request.query_params.get("q", "")
    return JSONResponse(content=market_search.search(query))


@app.get("/analysis", response_class=HTMLResponse)
async def analysis_page(request: Request):
    dashboard = build_dashboard()
    return templates.TemplateResponse(
        request=request,
        name="analysis.html",
        context={"request": request, "dashboard": dashboard},
    )


@app.get("/market/{symbol}", response_class=HTMLResponse)
async def market_page(request: Request, symbol: str):
    return RedirectResponse(url=f"/?symbol={symbol}")


@app.get("/api/fx-rate")
async def fx_rate_api():
    rate = service.data.exchange.get_rate("USD", "NOK")
    return JSONResponse(
        content={"base": rate.base, "target": rate.target, "rate": rate.rate}
    )


@app.get("/api/binance-candles")
async def binance_candles_api(request: Request):
    symbol = request.query_params.get("symbol", "BTCUSDT")
    interval = request.query_params.get("interval", "1h")
    limit = int(request.query_params.get("limit", "200"))
    return JSONResponse(
        content=binance_market_data.candles(
            symbol=symbol,
            interval=interval,
            limit=limit,
        )
    )


@app.get("/api/market-candles")
async def market_candles_api(request: Request):
    symbol = request.query_params.get("symbol", "NVDA")
    interval = request.query_params.get("interval", "1d")
    limit = int(request.query_params.get("limit", "200"))
    return JSONResponse(
        content=historical_market_data.candles(
            symbol=symbol,
            interval=interval,
            limit=limit,
        )
    )


@app.get("/api/multi-timeframe")
async def multi_timeframe_api(request: Request):
    symbol = request.query_params.get("symbol", "BTCUSDT")
    return JSONResponse(content=multi_timeframe.build(symbol))


@app.get("/api/strategy-research")
async def strategy_research_api(request: Request):
    symbol = request.query_params.get("symbol", "BTCUSDT")
    return JSONResponse(content=strategy_research.research(symbol))


@app.get("/portfolio", response_class=HTMLResponse)
async def portfolio_page(request: Request):
    dashboard = build_dashboard()
    return templates.TemplateResponse(
        request=request,
        name="portfolio.html",
        context={"request": request, "dashboard": dashboard},
    )


@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    dashboard = build_dashboard()
    return templates.TemplateResponse(
        request=request,
        name="settings.html",
        context={"request": request, "dashboard": dashboard},
    )


@app.post("/settings/language")
async def set_language(request: Request):
    form = await request.form()
    settings_service.set_language(form.get("language", "no"))
    return RedirectResponse(url="/settings", status_code=303)


@app.get("/agents", response_class=HTMLResponse)
async def agents_page(request: Request):
    dashboard = build_dashboard()
    return templates.TemplateResponse(
        request=request,
        name="agents.html",
        context={"request": request, "dashboard": dashboard},
    )
