"""Registry for ATLAS intelligence agents."""

from __future__ import annotations

from atlas.agents.base import MarketAgent


class AgentRegistry:
    """Stores and retrieves registered market-intelligence agents."""

    def __init__(self) -> None:
        self._agents: dict[str, MarketAgent] = {}

    def register(self, agent: MarketAgent) -> None:
        if agent.name in self._agents:
            raise ValueError(
                f"agent already registered: {agent.name}"
            )

        self._agents[agent.name] = agent

    def get(self, name: str) -> MarketAgent:
        try:
            return self._agents[name]
        except KeyError as exc:
            raise KeyError(
                f"unknown agent: {name}"
            ) from exc

    def all(self) -> tuple[MarketAgent, ...]:
        return tuple(self._agents.values())
