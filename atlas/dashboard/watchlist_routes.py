"""FastAPI-compatible watchlist route helper.

The current dashboard stores the personal watchlist in browser localStorage so
it is available without introducing server-side session state. This module is
kept as a reusable API helper for a future server-backed watchlist.
"""

from __future__ import annotations

from fastapi import APIRouter

from atlas.services.watchlist_service import WatchlistService


def create_watchlist_router(service: WatchlistService | None = None) -> APIRouter:
    watchlist = service or WatchlistService()
    router = APIRouter()

    @router.get("/api/watchlist")
    async def get_watchlist():
        return {"symbols": watchlist.get()}

    @router.post("/api/watchlist")
    async def add_watchlist(payload: dict):
        return {"symbols": watchlist.add(payload.get("symbol", ""))}

    @router.delete("/api/watchlist/{symbol:path}")
    async def remove_watchlist(symbol: str):
        return {"symbols": watchlist.remove(symbol)}

    return router
