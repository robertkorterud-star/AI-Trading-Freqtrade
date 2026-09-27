import pytest


@pytest.fixture(autouse=True)
def isolate_default_atlas_database(monkeypatch, tmp_path):
    monkeypatch.setenv(
        "ATLAS_DATABASE_PATH",
        str(tmp_path / "atlas.db"),
    )
