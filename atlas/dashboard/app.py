"""
ATLAS Dashboard
"""

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
from atlas.adapters.historical_market_data import (
    HistoricalMarketDataAdapter,
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
settings_service = service.data.settings
market_search = MarketSearchService()
historical_market_data = HistoricalMarketDataAdapter()

web_research = WebResearchAdapter()

strategy_research = AdaptiveStrategyResearchService(
    web_research=web_research,
)

intelligence_sources = IntelligenceSourceAdapter(
    web=web_research,
)


def get_language():
    return settings_service.get_language()


def build_dashboard(selected_symbol=None):
    return service.get_dashboard(
        selected_symbol=selected_symbol
    )


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):

    selected_symbol = request.query_params.get("symbol")

    dashboard = build_dashboard(
        selected_symbol=selected_symbol
    )

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "request": request,
            "dashboard": dashboard,
        },
    )


@app.get("/api/dashboard")
async def dashboard_api(request: Request):

    selected_symbol = request.query_params.get("symbol")

    dashboard = build_dashboard(
        selected_symbol=selected_symbol
    )

    return JSONResponse(
        content={
            "status": dashboard["status"],
            "version": dashboard["version"],
            "currency": dashboard["currency"],
            "technical": dashboard["technical"],
            "intelligence": dashboard["intelligence"],
            "decision": {
                "action": (
                    dashboard["decision"].action.value
                    if dashboard["decision"]
                    else None
                ),
                "confidence": (
                    dashboard["decision"].confidence
                    if dashboard["decision"]
                    else None
                ),
                "evidence": (
                    dashboard["decision"].evidence
                    if dashboard["decision"]
                    else None
                ),
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
async def analysis(
    request: Request,
    symbol: str | None = None,
):

    dashboard = service.get_dashboard(
        selected_symbol=symbol,
    )

    return templates.TemplateResponse(
        request=request,
        name="analysis.html",
        context={
            "request": request,
            "dashboard": dashboard,
        },
    )


@app.get("/api/market-search")
async def market_search_api(request: Request):

    query = request.query_params.get(
        "q",
        "",
    ).strip()

    if not query:
        return JSONResponse(
            content={"results": []}
        )

    results = market_search.search(
        query
    )

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
async def market_terminal(
    request: Request,
    symbol: str,
):
    normalized = symbol.strip().upper()

    results = market_search.search(
        normalized
    )

    asset = next(
        (
            item
            for item in results
            if item.get("symbol", "").upper()
            == normalized
        ),
        None,
    )

    if asset is None:
        return RedirectResponse(
            url="/markets?q="
            + normalized,
            status_code=302,
        )

    trading_status = settings_service.get_trading_status()

    dashboard = {
        "status": "ATLAS Online",
        "trading": trading_status,
    }

    return templates.TemplateResponse(
        request=request,
        name="market_terminal.html",
        context={
            "request": request,
            "asset": asset,
            "dashboard": dashboard,
        },
    )


@app.get("/api/fx-rate")
async def fx_rate_api(
    request: Request,
):
    source = request.query_params.get(
        "source",
        "USD",
    ).strip().upper()

    target = request.query_params.get(
        "target",
        "NOK",
    ).strip().upper()

    supported = {
        "USD",
        "NOK",
        "DKK",
        "SEK",
        "EUR",
    }

    if source not in supported or target not in supported:
        return JSONResponse(
            content={
                "error": "Unsupported currency."
            },
            status_code=400,
        )

    if source == target:
        return JSONResponse(
            content={
                "source": source,
                "target": target,
                "rate": 1.0,
            }
        )

    def usd_per_currency(currency: str) -> float:

        if currency == "USD":
            return 1.0

        symbol = f"USD{currency}=X"

        candles = historical_market_data.get(
            symbol,
            period="5d",
            interval="1d",
        )

        if not candles:
            raise ValueError(
                f"FX rate unavailable for {currency}."
            )

        return float(
            candles[-1]["close"]
        )

    try:
        source_usd_rate = usd_per_currency(
            source
        )

        target_usd_rate = usd_per_currency(
            target
        )

        # Convert source currency -> USD -> target currency.
        rate = (
            target_usd_rate /
            source_usd_rate
        )

        return JSONResponse(
            content={
                "source": source,
                "target": target,
                "rate": rate,
            }
        )

    except Exception as exc:
        return JSONResponse(
            content={
                "error": str(exc),
            },
            status_code=502,
        )


@app.get("/api/market-candles")
async def market_candles_api(
    request: Request,
):
    symbol = request.query_params.get(
        "symbol",
        "",
    ).strip().upper()

    period = request.query_params.get(
        "period",
        "3m",
    ).strip().lower()

    interval = request.query_params.get(
        "interval",
        "1h",
    ).strip().lower()

    valid_periods = {
        "1d": "1d",
        "5d": "5d",
        "1m": "1mo",
        "3m": "3mo",
        "6m": "6mo",
        "1y": "1y",
    }

    valid_intervals = {
        "5m": "5m",
        "15m": "15m",
        "1h": "1h",
        "4h": "4h",
        "1d": "1d",
    }

    if not symbol:
        return JSONResponse(
            content={
                "error": "Symbol is required."
            },
            status_code=400,
        )

    if period not in valid_periods:
        period = "3m"

    if interval not in valid_intervals:
        interval = "1h"

    try:
        candles = historical_market_data.get(
            symbol,
            period=valid_periods[period],
            interval=valid_intervals[interval],
        )
    except Exception as exc:
        return JSONResponse(
            content={
                "error": str(exc),
                "candles": [],
            },
            status_code=502,
        )

    return JSONResponse(
        content={
            "symbol": symbol,
            "period": period,
            "interval": interval,
            "candles": candles[-2000:],
        }
    )


@app.get("/markets", response_class=HTMLResponse)
async def markets(request: Request):

    query = request.query_params.get("q", "").strip()
    research_symbol = request.query_params.get("research", "").strip()

    results = market_search.search(query)

    trading_status = settings_service.get_trading_status()

    dashboard = {
        "status": "ATLAS Online",
        "trading": trading_status,
    }

    strategy_research_result = None

    if research_symbol:

        research_items = intelligence_sources.get(
            research_symbol
        )

        strategy_research_result = (
            strategy_research.research(
                symbol=research_symbol,
                research=research_items,
            )
        )

    return templates.TemplateResponse(
        request=request,
        name="markets.html",
        context={
            "request": request,
            "dashboard": dashboard,
            "query": query,
            "market_results": results,
            "strategy_research": strategy_research_result,
        },
    )


@app.get("/api/strategy-research")
async def strategy_research_api(request: Request):

    symbol = request.query_params.get("symbol", "").strip()

    if not symbol:
        return JSONResponse(
            content={
                "error": "Symbol is required."
            },
            status_code=400,
        )

    research_items = intelligence_sources.get(
        symbol
    )

    result = strategy_research.research(
        symbol=symbol,
        research=research_items,
    )

    return JSONResponse(
        content={
            "symbol": result.symbol,
            "strategies": [
                {
                    "name": strategy.name,
                    "timeframe": strategy.timeframe,
                    "entry_rule": strategy.entry_rule,
                    "exit_rule": strategy.exit_rule,
                    "stop_loss": strategy.stop_loss,
                    "take_profit": strategy.take_profit,
                    "source": strategy.source,
                    "reasoning": strategy.reasoning,
                }
                for strategy in result.strategies
            ],
            "backtests": [
                {
                    "strategy_name": backtest.strategy_name,
                    "symbol": backtest.symbol,
                    "trades": backtest.trades,
                    "wins": backtest.wins,
                    "losses": backtest.losses,
                    "win_rate": backtest.win_rate,
                    "total_return": backtest.total_return,
                    "profit_factor": backtest.profit_factor,
                    "max_drawdown": backtest.max_drawdown,
                }
                for backtest in result.backtests
            ],
        }
    )


@app.get("/portfolio", response_class=HTMLResponse)
async def portfolio(request: Request):

    dashboard = service.get_dashboard()

    return templates.TemplateResponse(
        request=request,
        name="portfolio.html",
        context={
            "request": request,
            "dashboard": dashboard,
        },
    )


@app.post("/settings")
async def update_settings(request: Request):

    form = await request.form()

    trading_mode = form.get("trading_mode")
    language = form.get("language")
    ai_provider = form.get("ai_provider")

    if trading_mode is not None:
        settings_service.set_trading_mode(
            trading_mode
        )

    if language is not None:
        settings_service.set_language(
            language
        )

    if ai_provider is not None:
        settings_service.set_ai_provider(
            ai_provider
        )

    return RedirectResponse(
        url="/settings",
        status_code=303,
    )


@app.get("/settings", response_class=HTMLResponse)
async def settings(request: Request):

    dashboard = service.get_dashboard()

    return templates.TemplateResponse(
        request=request,
        name="settings.html",
        context={
            "request": request,
            "dashboard": dashboard,
        },
    )


@app.get("/agents", response_class=HTMLResponse)
async def agents(request: Request):

    dashboard = service.get_dashboard()

    return templates.TemplateResponse(
        request=request,
        name="agents.html",
        context={
            "request": request,
            "dashboard": dashboard,
        },
    )
