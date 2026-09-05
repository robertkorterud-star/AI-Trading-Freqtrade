"""
ATLAS prediction inference input.

Builds live ML inference inputs from existing SignalEvidence without
reusing the supervised training example contract.
"""

from dataclasses import dataclass
from datetime import datetime

from atlas.trading.prediction_features import PredictionFeatureBuilder
from atlas.trading.signal_evidence import SignalEvidence


@dataclass(frozen=True, slots=True)
class PredictionInferenceExample:
    """Feature-only input for a live ML prediction."""

    features: dict[str, float]
    symbol: str
    timestamp: datetime


class PredictionInferenceBuilder:
    """Build live inference inputs from canonical signal evidence."""

    def __init__(
        self,
        feature_builder: PredictionFeatureBuilder | None = None,
    ):
        self.feature_builder = (
            feature_builder or PredictionFeatureBuilder()
        )

    def build(
        self,
        evidence: SignalEvidence,
        *,
        symbol: str,
        timestamp: datetime,
    ) -> PredictionInferenceExample:
        vector = self.feature_builder.build(evidence)

        return PredictionInferenceExample(
            features={
                name: float(value)
                for name, value in vars(vector).items()
            },
            symbol=symbol,
            timestamp=timestamp,
        )
