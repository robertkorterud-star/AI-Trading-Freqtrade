from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "atlas" / "dashboard" / "templates"
TRANSLATIONS = ROOT / "atlas" / "i18n" / "translations.py"


def test_dashboard_language_contract_covers_settings_and_portfolio():
    settings = (TEMPLATES / "settings.html").read_text(encoding="utf-8")
    portfolio = (TEMPLATES / "portfolio.html").read_text(encoding="utf-8")
    translations = TRANSLATIONS.read_text(encoding="utf-8")

    for marker in (
        "{{ t('settings') }}", "{{ t('trading_mode') }}", "{{ t('language') }}",
        "{{ t('ai_provider') }}", "{{ t('paper_trading') }}", "{{ t('safety') }}",
        "{{ t('save_settings') }}",
    ):
        assert marker in settings

    for marker in (
        "{{ t('portfolio') }}", "{{ t('total_equity') }}", "{{ t('performance') }}",
        "{{ t('positions') }}", "{{ t('trade_history') }}", "{{ t('no_open_positions') }}",
        "{{ t('no_trades_yet') }}",
    ):
        assert marker in portfolio

    for key in (
        'advisor_description', 'paper_description', 'safety_description', 'ai_provider',
        'active_provider', 'openai_description', 'ollama_description', 'on', 'off',
        'virtual_capital', 'paper_account_overview', 'profit_vault', 'performance', 'symbol',
        'value', 'no_open_positions', 'no_active_paper_positions', 'trade_history',
        'no_trades_yet', 'no_paper_trades',
    ):
        assert f'"{key}"' in translations


def test_dashboard_language_contract_covers_scanner():
    scanner = (TEMPLATES / "scanner.html").read_text(encoding="utf-8")
    translations = TRANSLATIONS.read_text(encoding="utf-8")

    for marker in (
        "{{ t('scanner_title') }}", "{{ t('scanner_description') }}",
        "{{ t('scanner_connected') }}", "{{ t('stocks') }}", "{{ t('crypto') }}",
        "{{ t('live_scanner_feed') }}", "{{ t('scanner_filters') }}",
        "{{ t('decision_pipeline') }}", "{{ t('current_scanner_rules') }}",
    ):
        assert marker in scanner

    for key in (
        'scanner_title', 'scanner_description', 'scanner_connected', 'stocks', 'crypto',
        'research_only', 'stocks_description', 'crypto_description', 'research_only_description',
        'live_scanner_feed', 'observations', 'eligible_candidates', 'scanner_filters',
        'search_symbol', 'market', 'all', 'catalyst', 'with_catalyst', 'without_catalyst',
        'sort_by', 'score', 'momentum', 'volume', 'breakout', 'liquidity', 'showing_candidates',
        'open_chart', 'no_market_observations', 'scanner_empty_description', 'decision_pipeline',
        'find_candidates', 'horizon_day_swing_position', 'technical_signals', 'deep_analysis',
        'before_paper_trade', 'current_scanner_rules', 'stock_min_price',
        'minimum_average_volume', 'minimum_current_volume', 'required',
    ):
        assert f'"{key}"' in translations


def test_dashboard_language_contract_covers_agents():
    agents = (TEMPLATES / "agents.html").read_text(encoding="utf-8")
    translations = TRANSLATIONS.read_text(encoding="utf-8")

    for marker in (
        "{{ t('agents') }}", "{{ t('agents_description') }}", "{{ t('predictions') }}",
        "{{ t('accuracy') }}", "{{ t('current_weight') }}", "{{ t('learning') }}",
        "{{ t('why_this_weight') }}", "{{ t('no_performance_history') }}",
    ):
        assert marker in agents

    for key in (
        'agents_description', 'predictions', 'correct', 'wrong', 'accuracy', 'current_weight',
        'safety_limit', 'learning', 'adaptive', 'building_history', 'why_this_weight',
        'stabilized', 'average', 'no_performance_history', 'no_agent_predictions_evaluated',
    ):
        assert f'"{key}"' in translations


def test_dashboard_language_contract_covers_analysis():
    analysis = (TEMPLATES / "analysis.html").read_text(encoding="utf-8")
    translations = TRANSLATIONS.read_text(encoding="utf-8")

    for marker in (
        "{{ t('market_overview') }}", "{{ t('watchlist') }}", "{{ t('symbol') }}",
        "{{ t('trend') }}", "{{ t('technical_analysis') }}", "{{ t('ai_decision') }}",
        "{{ t('confidence') }}", "{{ t('agreement') }}", "{{ t('dominant_influence') }}",
        "{{ t('learning') }}", "{{ t('robustness') }}", "{{ t('latest_news') }}",
        "{{ t('no_news_found') }}",
    ):
        assert marker in analysis

    for key in (
        'market_overview', 'watchlist', 'symbol', 'trend', 'technical_analysis', 'ai_decision',
        'confidence', 'agreement', 'dominant_influence', 'learning', 'adaptive', 'robustness',
        'level', 'signal', 'why_atlas', 'latest_news', 'no_news_found', 'positive', 'negative',
        'predictions', 'accuracy', 'decision_pipeline',
    ):
        assert f'"{key}"' in translations


def test_dashboard_language_contract_covers_markets_and_preserves_research_sections():
    markets = (TEMPLATES / "markets.html").read_text(encoding="utf-8")

    for marker in (
        "{{ t('markets') }}", "{{ t('all') }}", "{{ t('stocks') }}", "{{ t('crypto') }}",
        "market-search-trigger", "market-search-modal", "strategy-research-card",
        "strategy-learning-history", "strategy-backtest", "strategy-timing",
        "strategy-assessment", "research-source-summary", "/api/market-search?q=",
        "atlas.last_market_search", "/market/", "market-analyze-button",
        "market-research-button",
    ):
        assert marker in markets

    # Trading research terminology and machine-readable status values remain stable.
    for marker in ("PASS", "REJECT", "INCONCLUSIVE", "MA20", "MA50", "PF", "DD"):
        assert marker in markets
