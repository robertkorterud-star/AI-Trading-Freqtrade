"""ATLAS live dry-run dashboard server.

Read-only web UI around the existing dry-run pipeline. No exchange orders
are submitted by this module.
"""

from __future__ import annotations

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from atlas.adapters.binance import BinanceAdapter
from atlas.adapters.binance_market_data import BinanceMarketData
from atlas.trading.dry_run_loop import DryRunLoop
from atlas.agents import MomentumAgent, TrendAgent, VolumeAgent, VolatilityAgent


ROOT = Path(__file__).resolve().parent
INDEX = ROOT / "index.html"
SYMBOL = "BTCUSDT"
INTERVAL = "1m"
LIMIT = 150
POLL_SECONDS = 15


class DashboardState:
    def __init__(self) -> None:
        self.adapter = BinanceAdapter()
        self.market_data = BinanceMarketData(self.adapter)
        self.loop = DryRunLoop(
            agents=[
                TrendAgent(),
                MomentumAgent(),
                VolumeAgent(),
                VolatilityAgent(),
            ]
        )
        self.lock = threading.Lock()
        self.payload: dict = {"status": "starting"}
        self.markers: list[dict] = []
        self.last_execution_key: tuple | None = None

    def update(self) -> None:
        snapshot = self.market_data.snapshot(
            symbol=SYMBOL,
            interval=INTERVAL,
            limit=LIMIT,
        )
        result = self.loop.process(snapshot)
        candles = [
            {
                "time": int(c.timestamp),
                "open": c.open,
                "high": c.high,
                "low": c.low,
                "close": c.close,
                "volume": c.volume,
            }
            for c in snapshot.candles
        ]

        execution = result.execution
        action = getattr(execution.action, "value", str(execution.action))
        key = (snapshot.timestamp, action, execution.price, execution.quantity)
        if execution.executed and execution.quantity > 0 and key != self.last_execution_key:
            marker_action = "BUY" if action == "ENTER" else "SELL"
            self.markers.append({
                "time": int(snapshot.timestamp),
                "price": execution.price,
                "action": marker_action,
                "quantity": execution.quantity,
                "pnl": execution.realized_pnl,
            })
            self.markers = self.markers[-100:]
            self.last_execution_key = key

        decision_action = getattr(result.decision.action, "value", str(result.decision.action))
        with self.lock:
            self.payload = {
                "updated": time.time(),
                "symbol": result.symbol,
                "price": result.price,
                "candles": candles,
                "markers": list(self.markers),
                "intelligence": {
                    "score": result.intelligence_score,
                    "confidence": result.intelligence_confidence,
                },
                "agents": [
                    {
                        "name": o.agent,
                        "direction": o.direction,
                        "score": o.score,
                        "confidence": o.confidence,
                    }
                    for o in result.observations
                ],
                "algorithms": [
                    {
                        "name": s.algorithm,
                        "action": getattr(s.action, "value", str(s.action)),
                        "score": s.score,
                        "confidence": s.confidence,
                        "reasoning": list(s.reasoning),
                    }
                    for s in result.algorithm_signals
                ],
                "decision": {
                    "action": decision_action,
                    "score": result.decision.score,
                    "confidence": result.decision.confidence,
                    "risk_score": result.decision.risk_score,
                    "reason": result.decision.reason,
                },
                "execution": {
                    "action": action,
                    "quantity": execution.quantity,
                    "price": execution.price,
                    "target_position": execution.target_position,
                    "equity": execution.equity,
                    "realized_pnl": execution.realized_pnl,
                    "executed": execution.executed,
                    "reason": execution.reason,
                },
            }


def worker(state: DashboardState) -> None:
    while True:
        try:
            state.update()
        except Exception as exc:  # dashboard should stay alive on API errors
            with state.lock:
                state.payload = {"status": "error", "error": str(exc)}
        time.sleep(POLL_SECONDS)


class Handler(BaseHTTPRequestHandler):
    state: DashboardState

    def _send(self, status: int, content_type: str, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/":
            self._send(200, "text/html; charset=utf-8", INDEX.read_bytes())
            return
        if path == "/api/state":
            with self.state.lock:
                body = json.dumps(self.state.payload).encode("utf-8")
            self._send(200, "application/json; charset=utf-8", body)
            return
        self._send(404, "text/plain; charset=utf-8", b"Not found")

    def log_message(self, format: str, *args) -> None:
        return


def main() -> None:
    state = DashboardState()
    Handler.state = state
    threading.Thread(target=worker, args=(state,), daemon=True).start()
    server = ThreadingHTTPServer(("127.0.0.1", 8080), Handler)
    print("ATLAS dashboard: http://127.0.0.1:8080")
    print("Market data: Binance public REST API")
    print("Execution: VIRTUAL ONLY — no real orders")
    print(f"Refresh cycle: {POLL_SECONDS}s")
    server.serve_forever()


if __name__ == "__main__":
    main()
