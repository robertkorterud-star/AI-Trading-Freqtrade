"""Dashboard API payload helpers."""


def build_dashboard_api_payload(dashboard):
    """Serialize canonical dashboard state for the dashboard JSON API."""
    decision = dashboard["decision"]
    return {
        "status": dashboard["status"],
        "version": dashboard["version"],
        "currency": dashboard["currency"],
        "technical": dashboard["technical"],
        "intelligence": dashboard["intelligence"],
        "market": dashboard["market"],
        "market_scan": dashboard["market_scan"],
        "scanner": dashboard["scanner"],
        "portfolio": dashboard["portfolio"],
        "trading": dashboard["trading"],
        "decision": {
            "action": decision.action.value if decision else None,
            "confidence": decision.confidence if decision else None,
            "evidence": decision.evidence if decision else None,
        },
        "decision_explanation": dashboard["decision_explanation"],
        "decision_robustness": dashboard["decision_robustness"],
        "decision_influence": dashboard["decision_influence"],
        "analysts": dashboard["analysts"],
        "news": [
            {
                "title": article.get("title") if isinstance(article, dict) else article.title,
                "source": article.get("source") if isinstance(article, dict) else article.source,
                "summary": article.get("summary") if isinstance(article, dict) else article.summary,
                "url": article.get("url") if isinstance(article, dict) else article.url,
                "sentiment": article.get("sentiment") if isinstance(article, dict) else article.sentiment,
            }
            for article in dashboard["news"]
        ],
        "trade_history": dashboard["trade_history"],
        "trade_history_markers": dashboard["trade_history_markers"],
        "trade_history_period": dashboard["trade_history_period"],
        "trade_chart": dashboard["trade_chart"],
        "agent_performance": dashboard["agent_performance"],
    }
