from pathlib import Path


def test_legacy_risk_engine_stays_isolated_to_dry_run_trader():
    """Keep the legacy RiskEngine from leaking into modern ATLAS code."""
    atlas_root = Path(__file__).resolve().parents[1] / "atlas"
    allowed = {
        atlas_root / "risk" / "risk_engine.py",
        atlas_root / "trading" / "dry_run_trader.py",
    }

    offenders = []
    for path in atlas_root.rglob("*.py"):
        if path in allowed:
            continue
        source = path.read_text(encoding="utf-8")
        if "from atlas.risk.risk_engine import RiskEngine" in source:
            offenders.append(path.relative_to(atlas_root).as_posix())

    assert offenders == [], (
        "RiskEngine is a legacy compatibility boundary and must not leak "
        f"into modern ATLAS modules: {offenders}"
    )
