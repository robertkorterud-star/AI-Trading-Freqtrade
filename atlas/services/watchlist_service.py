"""Persistent personal watchlist for the ATLAS dashboard.

The watchlist is deliberately separate from Scanner candidates: Scanner discovers
opportunities, while this service stores the instruments the user explicitly wants
to follow.
"""

from __future__ import annotations

import json
from pathlib import Path
from threading import Lock


class WatchlistService:
    DEFAULT_SYMBOLS = ("BTC-USD", "ETH-USD", "SOL-USD", "NVDA")

    def __init__(self, path: str | Path = "data/watchlist.json") -> None:
        self.path = Path(path)
        self._lock = Lock()

    def get(self) -> list[str]:
        with self._lock:
            symbols = self._read()
            if symbols is None:
                symbols = list(self.DEFAULT_SYMBOLS)
                self._write(symbols)
            return symbols

    def add(self, symbol: str) -> list[str]:
        normalized = self._normalize(symbol)
        if not normalized:
            return self.get()
        with self._lock:
            symbols = self._read() or list(self.DEFAULT_SYMBOLS)
            if normalized not in symbols:
                symbols.append(normalized)
                self._write(symbols)
            return symbols

    def remove(self, symbol: str) -> list[str]:
        normalized = self._normalize(symbol)
        with self._lock:
            symbols = self._read() or list(self.DEFAULT_SYMBOLS)
            symbols = [item for item in symbols if item != normalized]
            self._write(symbols)
            return symbols

    @staticmethod
    def _normalize(symbol: str) -> str:
        value = str(symbol or "").strip().upper()
        if not value:
            return ""
        if value.endswith("USDT"):
            return value[:-4] + "-USD"
        if value.endswith("USDC"):
            return value[:-4] + "-USD"
        return value.replace("/", "-")

    def _read(self) -> list[str] | None:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return None
        if not isinstance(data, list):
            return None
        return [item for item in (self._normalize(value) for value in data) if item]

    def _write(self, symbols: list[str]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(symbols, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
