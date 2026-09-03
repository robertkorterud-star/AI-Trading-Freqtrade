from fastapi import FastAPI
from fastapi.testclient import TestClient

from atlas.dashboard.watchlist_routes import create_watchlist_router
from atlas.services.watchlist_service import WatchlistService


def test_watchlist_routes(tmp_path):
    app = FastAPI()
    app.include_router(
        create_watchlist_router(
            WatchlistService(tmp_path / "watchlist.json")
        )
    )
    client = TestClient(app)

    response = client.get("/api/watchlist")
    assert response.status_code == 200
    assert "BTC-USD" in response.json()["symbols"]

    response = client.post("/api/watchlist", json={"symbol": "AAPL"})
    assert response.status_code == 200
    assert "AAPL" in response.json()["symbols"]

    response = client.delete("/api/watchlist/AAPL")
    assert response.status_code == 200
    assert "AAPL" not in response.json()["symbols"]
