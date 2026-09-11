from datetime import datetime

from atlas.dashboard.dashboard_api import build_dashboard_api_payload
from atlas.models.action import Action


class _Decision:
    action = Action.BUY
    confidence = 91.0
    evidence = 88.0


class _Article:
    title = "ATLAS test article"
    source = "Test"
    summary = "Test summary"
    url = "https://example.com/article"
    sentiment = "positive"


def _dashboard():
    return {
        "status": "Running",
        "version": "0.8.1",
        "currency": {"base": "USD", "target": "NOK", "rate": 10.0},
        "technical": None,
        "intelligence": None,
        "market": [],
        "market_scan": [],
        "scanner": {},
        "portfolio": {},
        "trading": {"mode": "paper"},
        "decision": _Decision(),
        "decision_explanation": None,
        "decision_robustness": {},
        "decision_influence": {},
        "analysts": [],
        "news": [_Article()],
        "trade_history": [
            {
                "symbol": "XRP-USD",
                "action": "BUY",
                "timestamp": datetime(2026, 9, 11, 10, 0).isoformat(),
            }
        ],
        "trade_history_markers": [
            {
                "symbol": "XRP-USD",
                "action": "BUY",
                "price_usd": 1.34,
                "timestamp": "2026-09-11T10:00:00",
            }
        ],
        "trade_history_period": "1d",
        "trade_chart": {
            "period": "1d",
            "symbol": "XRP-USD",
            "trades": [],
            "markers": [],
        },
        "agent_performance": {},
    }


def test_dashboard_api_payload_exposes_trade_history_contract():
    payload = build_dashboard_api_payload(_dashboard())

    assert payload["trade_history_period"] == "1d"
    assert payload["trade_history"]
    assert payload["trade_history_markers"]
    assert payload["trade_chart"]["symbol"] == "XRP-USD"
    assert payload["trade_chart"]["markers"] == []


def test_dashboard_api_payload_keeps_existing_decision_and_news_contract():
    payload = build_dashboard_api_payload(_dashboard())

    assert payload["decision"] == {
        "action": "BUY",
        "confidence": 91.0,
        "evidence": 88.0,
    }
    assert payload["news"] == [
        {
            "title": "ATLAS test article",
            "source": "Test",
            "summary": "Test summary",
            "url": "https://example.com/article",
            "sentiment": "positive",
        }
    ]
