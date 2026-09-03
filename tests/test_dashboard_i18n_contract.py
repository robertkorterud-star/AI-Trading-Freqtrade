from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "atlas" / "dashboard" / "templates"
TRANSLATIONS = ROOT / "atlas" / "i18n" / "translations.py"


def test_dashboard_language_contract_covers_settings_and_portfolio():
    settings = (TEMPLATES / "settings.html").read_text(encoding="utf-8")
    portfolio = (TEMPLATES / "portfolio.html").read_text(encoding="utf-8")
    translations = TRANSLATIONS.read_text(encoding="utf-8")

    for marker in (
        "{{ t('settings') }}",
        "{{ t('trading_mode') }}",
        "{{ t('language') }}",
        "{{ t('ai_provider') }}",
        "{{ t('paper_trading') }}",
        "{{ t('safety') }}",
        "{{ t('save_settings') }}",
    ):
        assert marker in settings

    for marker in (
        "{{ t('portfolio') }}",
        "{{ t('total_equity') }}",
        "{{ t('performance') }}",
        "{{ t('positions') }}",
        "{{ t('trade_history') }}",
        "{{ t('no_open_positions') }}",
        "{{ t('no_trades_yet') }}",
    ):
        assert marker in portfolio

    for key in (
        'advisor_description', 'paper_description', 'safety_description',
        'ai_provider', 'active_provider', 'openai_description', 'ollama_description',
        'on', 'off', 'virtual_capital', 'paper_account_overview', 'profit_vault',
        'performance', 'symbol', 'value', 'no_open_positions',
        'no_active_paper_positions', 'trade_history', 'no_trades_yet', 'no_paper_trades',
    ):
        assert f'"{key}"' in translations
