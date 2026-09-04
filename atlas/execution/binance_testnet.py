"""Binance Spot Testnet execution adapter for ATLAS.

This adapter is deliberately locked to Binance Spot Testnet. It must never be
configured with a production Binance endpoint.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from atlas.execution.models import ExecutionRequest, ExecutionResult, ExecutionStatus


class BinanceTestnetExecutionAdapter:
    """Submit ATLAS orders only to Binance Spot Testnet."""

    BASE_URL = "https://testnet.binance.vision/api"

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        *,
        timeout: float = 10.0,
        recv_window: int = 5000,
        opener=None,
        clock=None,
    ) -> None:
        if not api_key.strip():
            raise ValueError("api_key must not be empty")
        if not api_secret.strip():
            raise ValueError("api_secret must not be empty")
        if recv_window <= 0:
            raise ValueError("recv_window must be greater than zero")

        self.api_key = api_key
        self.api_secret = api_secret
        self.timeout = timeout
        self.recv_window = recv_window
        self._opener = opener or urlopen
        self._clock = clock or time.time

    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        """Submit one approved order to Spot Testnet and return its result."""
        params: dict[str, object] = {
            "symbol": request.symbol.replace("/", "").upper(),
            "side": request.action.value,
            "type": "LIMIT" if request.price is not None else "MARKET",
            "quantity": self._format_number(request.quantity),
            "timestamp": int(self._clock() * 1000),
            "recvWindow": self.recv_window,
            "newOrderRespType": "ACK",
        }
        if request.price is not None:
            params["price"] = self._format_number(request.price)
            params["timeInForce"] = "GTC"

        query = urlencode(params)
        signature = hmac.new(
            self.api_secret.encode("utf-8"),
            query.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        url = f"{self.BASE_URL}/v3/order?{query}&signature={signature}"
        http_request = Request(
            url,
            headers={
                "Accept": "application/json",
                "X-MBX-APIKEY": self.api_key,
            },
            method="POST",
        )

        try:
            with self._opener(http_request, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            raise RuntimeError(
                f"Binance Spot Testnet API error {exc.code}: "
                f"{self._error_message(exc)}"
            ) from exc
        except URLError as exc:
            raise RuntimeError(
                f"Binance Spot Testnet connection error: {exc.reason}"
            ) from exc
        except TimeoutError as exc:
            raise RuntimeError("Binance Spot Testnet request timed out") from exc
        except json.JSONDecodeError as exc:
            raise RuntimeError("Binance Spot Testnet returned invalid JSON") from exc

        if not isinstance(payload, dict):
            raise RuntimeError("Binance Spot Testnet returned an invalid order response")

        order_id = payload.get("orderId")
        return ExecutionResult(
            status=ExecutionStatus.ACCEPTED,
            symbol=request.symbol,
            action=request.action,
            quantity=request.quantity,
            message="order submitted to Binance Spot Testnet",
            external_order_id=str(order_id) if order_id is not None else None,
        )

    @staticmethod
    def _format_number(value: float) -> str:
        return format(value, ".15g")

    @staticmethod
    def _error_message(exc: HTTPError) -> str:
        try:
            payload = exc.read().decode("utf-8")
            data = json.loads(payload)
            if isinstance(data, dict):
                return str(data.get("msg", data.get("code", payload)))
            return payload
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return str(exc.reason)
