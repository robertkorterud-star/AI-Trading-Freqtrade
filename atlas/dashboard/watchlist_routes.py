"""Watchlist API helpers used by the dashboard application."""

from __future__ import annotations

from flask import jsonify, request

from atlas.services.watchlist_service import WatchlistService


def register_watchlist_routes(app, service: WatchlistService | None = None) -> None:
    watchlist = service or WatchlistService()

    @app.get("/api/watchlist")
    def get_watchlist():
        return jsonify({"symbols": watchlist.get()})

    @app.post("/api/watchlist")
    def add_watchlist():
        payload = request.get_json(silent=True) or {}
        return jsonify({"symbols": watchlist.add(payload.get("symbol", ""))})

    @app.delete("/api/watchlist/<path:symbol>")
    def remove_watchlist(symbol: str):
        return jsonify({"symbols": watchlist.remove(symbol)})
