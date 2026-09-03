"""Small integration helper for registering ATLAS watchlist routes."""

from atlas.dashboard.watchlist_routes import register_watchlist_routes


def setup_watchlist(app):
    register_watchlist_routes(app)
    return app
