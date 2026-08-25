from atlas.market.asset_discovery import DiscoveryScore


class CandidateSelector:
    """Select the strongest assets for deeper ATLAS analysis."""

    def select(
        self,
        candidates: list[DiscoveryScore],
        limit: int | None = None,
        minimum_score: float = 0.0,
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

        return valid[:max(0, limit)]
