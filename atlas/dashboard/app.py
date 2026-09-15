"""
ATLAS Dashboard
"""

import asyncio
from datetime import datetime
import json
import time

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from atlas.i18n.translations import translate
from atlas.dashboard.dashboard_service import DashboardService
from atlas.dashboard.dashboard_api import build_dashboard_api_payload
from atlas.services.settings_service import SettingsService
from atlas.services.market_search_service import MarketSearchService
from atlas.services.adaptive_strategy_research_service import AdaptiveStrategyResearchService
from atlas.adapters.intelligence_sources import IntelligenceSourceAdapter
from atlas.adapters.web_research import WebResearchAdapter
from atlas.adapters.binance_market_data import BinanceMarketDataAdapter
from atlas.adapters.historical_market_data import HistoricalMarketDataAdapter
from atlas.services.multi_timeframe_service import MultiTimeframeService
from atlas.core.config import AtlasConfig
from atlas.database.connection import Database
from atlas.database.schema import initialize_database
from atlas.database.event_repository import AtlasEventRepository
from atlas.security.auth_middleware import AuthenticationMiddleware
from atlas.security.auth_service import AuthService

app = FastAPI(title="ATLAS Dashboard")
app.mount("/static", StaticFiles(directory="atlas/dashboard/static"), name="static")
templates = Jinja2Templates(directory="atlas/dashboard/templates")

config = AtlasConfig(load_persisted_settings=True)
database = Database(config.database_path)
initialize_database(database)
auth_service = AuthService(database)
app.add_middleware(AuthenticationMiddleware, auth_service=auth_service)

event_repository = AtlasEventRepository(database)
service = DashboardService(config=config)
settings_service = SettingsService(config=config)
market_search = MarketSearchService()
historical_market_data = HistoricalMarketDataAdapter()
binance_market_data = BinanceMarketDataAdapter()
web_research = WebResearchAdapter()
strategy_research = AdaptiveStrategyResearchService(web_research=web_research)
intelligence_sources = IntelligenceSourceAdapter(web=web_research)
multi_timeframe = MultiTimeframeService(market_data=historical_market_data)

STRATEGY_RESEARCH_CACHE_TTL = 300.0
_strategy_research_cache = {}
_intelligence_sources_cache = {}


def get_language():
    return settings_service.get_language()


def template_translate(key):
    return translate(get_language(), key)


templates.env.globals["t"] = template_translate
templates.env.globals["get_language"] = get_language


def get_cached_intelligence_sources(symbol: str):
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
    now = time.monotonic()
    cached = _strategy_research_cache.get(symbol)
    if cached is not None:
        created_at, result = cached
        if now - created_at < STRATEGY_RESEARCH_CACHE_TTL:
            return result
    result = strategy_research.research(symbol=symbol, research=research_items)
    _strategy_research_cache[symbol] = (now, result)
    return result


def build_dashboard(selected_symbol=None, trade_history_period="1d"):
    return service.get_dashboard(
        selected_symbol=selected_symbol,
        trade_history_period=trade_history_period,
    )


def _normalize_candle_timestamp(value) -> float:
    """Return a Lightweight Charts-compatible Unix timestamp in seconds."""
    if isinstance(value, (int, float)):
        numeric = float(value)
        return numeric / 1000.0 if numeric > 10_000_000_000 else numeric

    text = str(value).strip()
    if not text:
        raise ValueError("Candle timestamp is empty")

    try:
        numeric = float(text)
        return numeric / 1000.0 if numeric > 10_000_000_000 else numeric
    except ValueError:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return parsed.timestamp()


def _serialize_binance_candle(candle) -> dict:
    return {
        "timestamp": _normalize_candle_timestamp(candle.timestamp),
        "open": float(candle.open),
        "high": float(candle.high),
        "low": float(candle.low),
        "close": float(candle.close),
        "volume": float(candle.volume),
    }


def _normalize_market_candles(candles: list[dict]) -> list[dict]:
    return [
        {
            **candle,
            "timestamp": _normalize_candle_timestamp(candle["timestamp"]),
        }
        for candle in candles
    ]


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    if auth_service.get_user_by_session(request.cookies.get("atlas_session")):
        return RedirectResponse(url="/", status_code=303)
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"request": request, "error": None},
    )


@app.post("/login", response_class=HTMLResponse)
async def login(request: Request):
    form = await request.form()
    username = str(form.get("username", ""))
    password = str(form.get("password", ""))
    user = auth_service.authenticate(username, password)
    if user is None:
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={"request": request, "error": "Feil brukernavn eller passord."},
            status_code=401,
        )

    token = auth_service.create_session(user.id)
    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie(
        "atlas_session",
        token,
        httponly=True,
        samesite="lax",
        secure=request.url.scheme == "https",
        max_age=12 * 60 * 60,
    )
    return response


@app.post("/logout")
async def logout(request: Request):
    token = request.cookies.get("atlas_session")
    auth_service.revoke_session(token)
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie("atlas_session")
    return response


@app.get("/setup", response_class=HTMLResponse)
async def setup_page(request: Request):
    with database.connect() as connection:
        count = connection.execute("SELECT COUNT(*) AS count FROM users").fetchone()["count"]
    if count:
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse(
        request=request,
        name="setup.html",
        context={"request": request, "error": None},
    )


@app.post("/setup", response_class=HTMLResponse)
async def setup(request: Request):
    with database.connect() as connection:
        count = connection.execute("SELECT COUNT(*) AS count FROM users").fetchone()["count"]
    if count:
        return RedirectResponse(url="/login", status_code=303)

    form = await request.form()
    username = str(form.get("username", ""))
    password = str(form.get("password", ""))
    confirm = str(form.get("confirm_password", ""))
    if not username.strip() or len(password) < 12 or password != confirm:
        return templates.TemplateResponse(
            request=request,
            name="setup.html",
            context={
                "request": request,
                "error": "Brukernavn må fylles ut. Passord må være minst 12 tegn og matche.",
            },
            status_code=400,
        )

    user = auth_service.create_user(username, password, role="ADMIN")
    token = auth_service.create_session(user.id)
    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie(
        "atlas_session",
        token,
        httponly=True,
        samesite="lax",
        secure=request.url.scheme == "https",
        max_age=12 * 60 * 60,
    )
    return response


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    selected_symbol = request.query_params.get("symbol")
    trade_history_period = request.query_params.get("trade_history_period", "1d").strip().lower()
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "request": request,
            "dashboard": build_dashboard(
                selected_symbol=selected_symbol,
                trade_history_period=trade_history_period,
            ),
        },
    )



@app.get("/portfolio", response_class=HTMLResponse)
async def portfolio_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="portfolio.html",
        context={"request": request, "dashboard": build_dashboard()},
    )



@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="settings.html",
        context={"request": request, "dashboard": build_dashboard()},
    )


@app.post("/settings")
async def update_settings(request: Request):
    form = await request.form()

    trading_mode = form.get("trading_mode")
    if trading_mode:
        settings_service.set_trading_mode(str(trading_mode))

    language = form.get("language")
    if language:
        settings_service.set_language(str(language))

    ai_provider = form.get("ai_provider")
    if ai_provider:
        settings_service.set_ai_provider(str(ai_provider))

    accumulation_drop_pct = form.get("accumulation_drop_pct")
    if accumulation_drop_pct is not None and str(accumulation_drop_pct).strip():
        settings_service.set_accumulation_drop_pct(str(accumulation_drop_pct))

    return RedirectResponse(url="/settings", status_code=303)


@app.get("/scanner", response_class=HTMLResponse)
async def scanner(request: Request):
    scanner_data = service.get_scanner()
    scanner_data.setdefault(
        "rules",
        {
            "stock_min_price": 1.0,
            "minimum_average_volume": 100_000.0,
            "minimum_current_volume": 100_000.0,
        },
    )
    return templates.TemplateResponse(
        request=request,
        name="scanner.html",
        context={"request": request, "dashboard": {"scanner": scanner_data}},
    )


@app.get("/api/dashboard")
async def dashboard_api(request: Request):
    trade_history_period = request.query_params.get("trade_history_period", "1d").strip().lower()
    dashboard = build_dashboard(
        selected_symbol=request.query_params.get("symbol"),
        trade_history_period=trade_history_period,
    )
    return JSONResponse(content=build_dashboard_api_payload(dashboard))


@app.get("/api/atlas-events")
async def atlas_events(request: Request):
    """Stream new ATLAS state changes without replaying history on page load."""
    raw_last_event_id = request.headers.get("Last-Event-ID")
    try:
        last_event_id = int(raw_last_event_id) if raw_last_event_id else None
    except ValueError:
        last_event_id = None

    async def event_stream():
        # A freshly loaded dashboard must start after the current event log.
        # Otherwise each page reload would replay the same historical event,
        # trigger another reload, and send the user back to the top repeatedly.
        cursor = event_repository.latest_id() if last_event_id is None else last_event_id
        while not await request.is_disconnected():
            events = event_repository.after(cursor)
            if events:
                for event in events:
                    cursor = event["id"]
                    yield (
                        f"id: {event['id']}\n"
                        f"event: {event['type']}\n"
                        f"data: {json.dumps(event['payload'], ensure_ascii=False, sort_keys=True)}\n\n"
                    )
                continue

            # SQLite is the cross-process event transport. This is deliberately
            # a cheap event-log check, not a dashboard rebuild or market/API call.
            yield ": heartbeat\n\n"
            await asyncio.sleep(1.0)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
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


@app.get("/analysis", response_class=HTMLResponse)
async def analysis_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="analysis.html",
        context={"request": request, "dashboard": build_dashboard()},
    )


@app.get("/market/{symbol}", response_class=HTMLResponse)
async def market_page(request: Request, symbol: str):
    normalized = symbol.strip().upper()
    return RedirectResponse(url=f"/?symbol={normalized}")


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
        candles = historical_market_data.get(f"USD{currency}=X", period="5d", interval="1d")
        if not candles:
            raise ValueError(f"FX rate unavailable for {currency}.")
        return float(candles[-1]["close"])

    try:
        rate = usd_per_currency(target) / usd_per_currency(source)
        return JSONResponse(content={"source": source, "target": target, "rate": rate})
    except Exception as exc:
        return JSONResponse(content={"error": str(exc)}, status_code=502)


@app.get("/api/binance-candles")
async def binance_candles_api(request: Request):
    symbol = request.query_params.get("symbol", "BTCUSDT").strip().upper()
    interval = request.query_params.get("interval", "1h").strip().lower()
    try:
        limit = max(1, min(int(request.query_params.get("limit", "200")), 1000))
    except ValueError:
        limit = 200

    try:
        candles = binance_market_data.get_candles(symbol=symbol, interval=interval, limit=limit)
    except Exception as exc:
        return JSONResponse(content={"symbol": symbol, "interval": interval, "candles": [], "error": str(exc)}, status_code=502)

    return JSONResponse(
        content={
            "symbol": symbol,
            "interval": interval,
            "candles": [_serialize_binance_candle(candle) for candle in candles],
        }
    )


@app.get("/api/market-candles")
async def market_candles_api(request: Request):
    symbol = request.query_params.get("symbol", "NVDA").strip().upper()
    period = request.query_params.get("period", "3m").strip().lower()
    interval = request.query_params.get("interval", "1h").strip().lower()
    valid_periods = {
        "1d": "1d",
        "5d": "5d",
        "1m": "1mo",
        "3m": "3mo",
        "6m": "6mo",
        "1y": "1y",
        "5y": "5y",
    }
    valid_intervals = {"5m": "5m", "15m": "15m", "1h": "1h", "4h": "4h", "1d": "1d"}
    if not symbol:
        return JSONResponse(content={"error": "Symbol is required."}, status_code=400)
    period = period if period in valid_periods else "3m"
    interval = interval if interval in valid_intervals else "1h"
    try:
        candles = historical_market_data.get(symbol, period=valid_periods[period], interval=valid_intervals[interval])
        candles = _normalize_market_candles(candles)
    except Exception as exc:
        return JSONResponse(content={"error": str(exc), "candles": []}, status_code=502)
    return JSONResponse(content={"symbol": symbol, "period": period, "interval": interval, "candles": candles[-2000:]})


@app.get("/api/multi-timeframe")
async def multi_timeframe_api(request: Request):
    symbol = request.query_params.get("symbol", "BTCUSDT")
    return JSONResponse(content=multi_timeframe.build(symbol))


@app.get("/markets", response_class=HTMLResponse)
async def markets(request: Request):
    query = request.query_params.get("q", "").strip()
    research_symbol = request.query_params.get("research", "").strip()
    results = market_search.search(query)
    dashboard = {"status": "ATLAS Online", "trading": settings_service.get_trading_status()}
    strategy_research_result = None
    if research_symbol:
        research_items = get_cached_intelligence_sources(research_symbol)
        strategy_research_result = get_cached_strategy_research(research_symbol, research_items)
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
        return JSONResponse(content={"error": "Symbol is required."}, status_code=400)
    research_items = get_cached_intelligence_sources(symbol)
    result = get_cached_strategy_research(symbol, research_items)
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
