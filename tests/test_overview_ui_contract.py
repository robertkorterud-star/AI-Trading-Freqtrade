from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "atlas" / "dashboard" / "templates" / "index.html"
STYLE = ROOT / "atlas" / "dashboard" / "static" / "overview.css"
BASE = ROOT / "atlas" / "dashboard" / "templates" / "base.html"


def test_overview_template_has_command_center_sections():
    text = TEMPLATE.read_text(encoding="utf-8")

    for marker in (
        '{{ t("market_overview") }}',
        '{{ t("market_pulse") }}',
        '{{ t("opportunities") }}',
        '{{ t("intelligence") }}',
        '{{ t("watchlist") }}',
        '{{ t("news_events") }}',
        "/scanner",
        "/markets",
        "/market/{{ dashboard.intelligence.symbol }}",
    ):
        assert marker in text


def test_overview_market_workspace_supports_trade_history_chart_selection():
    text = TEMPLATE.read_text(encoding="utf-8")

    for marker in (
        'id="atlas-candles"',
        'id="overview-market-title"',
        'id="overview-chart-status"',
        'id="atlas-trade-detail"',
        "trade_chart.symbol",
        "trade_chart.trades",
        "markerForTrade",
        "series.setMarkers(markerData)",
        "'/api/market-candles?symbol=",
        "overview-period",
        'data-period="1d"',
        'data-period="1w"',
        'data-period="1m"',
        'data-period="all"',
    ):
        assert marker in text


def test_overview_uses_existing_dashboard_data_contract():
    text = TEMPLATE.read_text(encoding="utf-8")

    for field in (
        "dashboard.portfolio.total_equity_nok",
        "dashboard.portfolio.cash_nok",
        "dashboard.portfolio.position_count",
        "dashboard.portfolio.return_percent",
        "dashboard.market_scan",
        "dashboard.market",
        "dashboard.intelligence.confidence",
        "dashboard.intelligence.evidence",
        "dashboard.intelligence.agreement",
        "dashboard.decision_robustness.robustness",
        "dashboard.decision_robustness.level",
        "dashboard.decision_influence.dominant_action",
        "dashboard.news",
    ):
        assert field in text


def test_overview_styles_are_loaded_and_responsive():
    base = BASE.read_text(encoding="utf-8")
    style = STYLE.read_text(encoding="utf-8")

    assert '/static/overview.css' in base
    for marker in (
        ".overview-page",
        ".overview-grid",
        ".overview-columns",
        ".overview-pulse-grid",
        ".overview-table",
        ".overview-intelligence",
        "@media (max-width:700px)",
    ):
        assert marker in style
