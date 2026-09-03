from pathlib import Path


SETTINGS_TEMPLATE = Path(
    "atlas/dashboard/templates/settings.html"
)


def test_settings_page_contains_trading_mode_controls():

    text = SETTINGS_TEMPLATE.read_text()

    assert "{{ t('trading_mode') }}" in text
    assert "{{ t('advisor') }}" in text
    assert "{{ t('paper_dry_run') }}" in text
    assert "paper_trading" in text


def test_settings_page_uses_active_trading_mode():

    text = SETTINGS_TEMPLATE.read_text()

    assert "dashboard.trading.mode" in text
    assert "dashboard.trading.paper_trading" in text


def test_settings_page_contains_save_form():

    text = SETTINGS_TEMPLATE.read_text()

    assert '<form' in text
    assert 'action="/settings"' in text
    assert 'method="post"' in text
    assert "{{ t('save_settings') }}" in text


def test_settings_page_marks_active_trading_mode():

    text = SETTINGS_TEMPLATE.read_text()

    assert 'value="advisor"' in text
    assert 'value="paper"' in text
    assert 'dashboard.trading.mode == "advisor"' in text
    assert 'dashboard.trading.mode == "paper"' in text


def test_settings_page_contains_ai_provider_controls():

    text = SETTINGS_TEMPLATE.read_text()

    assert "{{ t('ai_provider') }}" in text
    assert "OpenAI" in text
    assert "Ollama" in text
    assert 'name="ai_provider"' in text


def test_settings_page_uses_active_ai_provider():

    text = SETTINGS_TEMPLATE.read_text()

    assert "dashboard.trading.ai_provider" in text
    assert 'value="openai"' in text
    assert 'value="ollama"' in text
