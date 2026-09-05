"""
ATLAS live prediction signal service.

Bridges canonical SignalEvidence to the existing ML prediction signal
without introducing new decision logic or a second feature contract.
"""

from datetime import datetime

from atlas.algorithms.base import AlgorithmSignal
from atlas.trading.ml_signal import MLPredictionSignal
from atlas.trading.prediction_inference import PredictionInferenceBuilder
from atlas.trading.signal_evidence import SignalEvidence


class PredictionSignalService:
    """Build a live ML signal from canonical signal evidence."""

    def __init__(
        self,
        signal: MLPredictionSignal,
        inference_builder: PredictionInferenceBuilder | None = None,
    ):
        self.signal = signal
        self.inference_builder = (
            inference_builder or PredictionInferenceBuilder()
        )

    def predict(
        self,
        evidence: SignalEvidence,
        *,
        symbol: str,
        timestamp: datetime,
    ) -> AlgorithmSignal:
        """Convert existing evidence into the model's algorithm signal."""
        example = self.inference_builder.build(
            evidence,
            symbol=symbol,
            timestamp=timestamp,
        )
        return self.signal.predict(example)
