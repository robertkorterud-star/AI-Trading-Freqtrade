"""
ATLAS Dashboard
"""

from datetime import datetime
import time

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from atlas.i18n.translations import translate
from atlas.dashboard.dashboard_service import DashboardService
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


def build_dashboard(selected_symbol=None):
    return service.get_dashboard(selected_symbol=selected_symbol)


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
