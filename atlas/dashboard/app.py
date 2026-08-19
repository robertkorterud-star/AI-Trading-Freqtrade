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
from atlas.services.strategy_research_service import StrategyResearchService
from atlas.adapters.intelligence_sources import IntelligenceSourceAdapter

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
strategy_research = StrategyResearchService()
intelligence_sources = IntelligenceSourceAdapter()


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


@app.get("/markets", response_class=HTMLResponse)
async def markets(request: Request):

    query = request.query_params.get("q", "").strip()
    research_symbol = request.query_params.get("research", "").strip()

    results = market_search.search(query)

    dashboard = service.get_dashboard()

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
