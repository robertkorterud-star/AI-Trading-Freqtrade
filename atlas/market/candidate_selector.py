from atlas.market.asset_discovery import DiscoveryScore


class CandidateSelector:
    """Select the strongest assets for deeper ATLAS analysis."""

    def select(
        self,
        candidates: list[DiscoveryScore],
        limit: int | None = None,
        minimum_score: float = 0.0,
        trigger_symbol: str | None = None,
    ) -> list[DiscoveryScore]:
        """Return highest-scoring candidates meeting the threshold."""

        valid = [
            candidate
            for candidate in candidates
            if candidate.score >= minimum_score
        ]

        valid.sort(
            key=lambda candidate: candidate.score,
            reverse=True,
        )

        if limit is None:
            return valid

        limit = max(0, limit)
        selected = valid[:limit]

        if not trigger_symbol or limit == 0:
            return selected

        normalized_trigger = trigger_symbol.strip().upper()

        if any(
            candidate.symbol.strip().upper() == normalized_trigger
            for candidate in selected
        ):
            return selected

        triggered = next(
            (
                candidate
                for candidate in valid
                if candidate.symbol.strip().upper()
                == normalized_trigger
            ),
            None,
        )

        if triggered is None:
            return selected

        return selected[:limit - 1] + [triggered]
