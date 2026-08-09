"""
ATLAS Dashboard
"""

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from atlas.dashboard.dashboard_service import DashboardService

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


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):

    dashboard = service.get_dashboard()

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "request": request,
            "dashboard": dashboard,
        },
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