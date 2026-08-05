from dataclasses import dataclass


@dataclass
class DashboardModel:

    status: str

    version: str

    symbol: str

    decision: str

    evidence: float

    confidence: float

    capital: float