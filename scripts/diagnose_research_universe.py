"""Manual diagnostic for widening ATLAS research candidates without changing runtime logic.

Run from the repository root:

    python scripts/diagnose_research_universe.py

This is intentionally a diagnostic, not a production runtime path.
"""

from __future__ import annotations

from atlas.core.config import AtlasConfig
from atlas.core.engine import AtlasEngine
from atlas.services.settings_service import SettingsService


RESEARCH_LIMIT = 40


def main() -> None:
    config = SettingsService(
        config=AtlasConfig(load_persisted_settings=True)
    ).get_config()

    print(f"Trading mode : {config.trading_mode}")
    print(f"Paper trading: {config.paper_trading}")

    if config.trading_mode != "paper" or not config.paper_trading:
        raise SystemExit("STOPP: ATLAS is not in paper mode.")

    engine = AtlasEngine(config=config)

    print(f"\nFetching up to {RESEARCH_LIMIT} research candidates ...", flush=True)
    candidates = engine.research_candidates(limit=RESEARCH_LIMIT)

    print(f"Research candidates: {len(candidates)}")
    for number, candidate in enumerate(candidates, 1):
        print(
            f"{number:>2}. {candidate.symbol:<18} "
            f"score={candidate.score:>7.2f} "
            f"source={candidate.source}"
        )

    before = set(engine.asset_universe.symbols())
    added = engine.expand_universe_from_candidates(candidates)
    after = set(engine.asset_universe.symbols())

    print("\n========== RESEARCH UNIVERSE ==========")
    print(f"Requested limit : {RESEARCH_LIMIT}")
    print(f"Candidates      : {len(candidates)}")
    print(f"Resolved/added  : {added}")
    print(f"Active universe : {engine.asset_universe.count()}")
    print("New symbols     :", ", ".join(sorted(after - before)) or "(none)")
    print("All symbols     :", ", ".join(engine.asset_universe.symbols()))
    print("=======================================")

    print("\nTop 3 candidates reaching deep ATLAS analysis:")
    discovered = engine.discover_candidates(limit=3)
    if not discovered:
        print("(none)")
    for number, candidate in enumerate(discovered, 1):
        print(
            f"{number}. {candidate.symbol:<18} "
            f"score={candidate.score:>7.2f}"
        )

    print("\nRunning one canonical ATLAS cycle ...\n", flush=True)
    engine.start()


if __name__ == "__main__":
    main()
