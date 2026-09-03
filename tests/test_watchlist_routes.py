from flask import Flask

from atlas.dashboard.watchlist_routes import register_watchlist_routes
from atlas.services.watchlist_service import WatchlistService


def test_watchlist_routes(tmp_path):
    app = Flask(__name__)
    register_watchlist_routes(app, WatchlistService(tmp_path / "watchlist.json"))
    client = app.test_client()

    response = client.get("/api/watchlist")
    assert response.status_code == 200
    assert "BTC-USD" in response.get_json()["symbols"]

    response = client.post("/api/watchlist", json={"symbol": "AAPL"})
    assert response.status_code == 200
    assert "AAPL" in response.get_json()["symbols"]

    response = client.delete("/api/watchlist/AAPL")
    assert response.status_code == 200
    assert "AAPL" not in response.get_json()["symbols"]
