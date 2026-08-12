from pathlib import Path


NAVBAR = Path(
    "atlas/dashboard/templates/components/navbar.html"
)


def test_navbar_contains_settings_link():

    text = NAVBAR.read_text()

    assert 'href="/settings"' in text
    assert "Settings" in text
