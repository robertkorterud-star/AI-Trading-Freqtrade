"""
Agent Registry
"""

from atlas.agents.base_agent import BaseAgent


class AgentRegistry:
    """Keeps track of all registered analysts."""

    def __init__(self) -> None:
        self._agents: dict[str, BaseAgent] = {}

    def register(self, agent: BaseAgent) -> None:
        self._agents[agent.name] = agent

    def get(self, name: str) -> BaseAgent | None:
        return self._agents.get(name)

    def get_all(self) -> list[BaseAgent]:
        return list(self._agents.values())

    def count(self) -> int:
        return len(self._agents)

    def analyze_all(self, symbol: str):
        """Run all registered analysts."""

        results = []

        for agent in self.get_all():
            results.append(agent.analyze(symbol))

        return results