from pathlib import Path


def test_legacy_risk_engine_stays_isolated_to_compatibility_boundaries():
    """Keep the legacy RiskEngine out of modern decision/risk modules."""
    atlas_root = Path(__file__).resolve().parents[1] / "atlas"
    allowed = {
        atlas_root / "risk" / "risk_engine.py",
        # The dry-run trader is the legacy compatibility owner.
        atlas_root / "trading" / "dry_run_trader.py",
        # AtlasEngine is the composition root that wires the legacy paper path.
        atlas_root / "core" / "engine.py",
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
