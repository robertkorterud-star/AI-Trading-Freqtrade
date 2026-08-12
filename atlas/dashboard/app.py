"""
ATLAS Dashboard
"""

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from atlas.dashboard.dashboard_service import DashboardService
from atlas.services.settings_service import SettingsService

app = FastAPI(title="ATLAS Dashboard")

app.mount(
    "/static",
    StaticFiles(directory="atlas/dashboard/static"),
    name="static",
)

templates = Jinja2Templates(
    directory="atlas/dashboard/templates"
)

service = DashboardService()
settings_service = service.data.settings


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
        }
    )


@app.get("/analysis", response_class=HTMLResponse)
async def analysis(request: Request):

    dashboard = service.get_dashboard()

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

    dashboard = service.get_dashboard()

    return templates.TemplateResponse(
        request=request,
        name="markets.html",
        context={
            "request": request,
            "dashboard": dashboard,
        },
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

    if trading_mode is not None:
        settings_service.set_trading_mode(
            trading_mode
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
