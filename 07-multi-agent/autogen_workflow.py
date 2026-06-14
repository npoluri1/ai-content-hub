"""
Multi-Agent system using AutoGen patterns — specialized agents with orchestration.
"""

from typing import Protocol

class Agent(Protocol):
    name: str
    role: str

    def execute(self, task: str) -> str: ...

class ResearcherAgent:
    def __init__(self):
        self.name = "Researcher"
        self.role = "Cross-references sources, evaluates credibility"

    def execute(self, task: str) -> str:
        return f"[Researcher] Analyzed: {task} — found 3 credible sources"

class WriterAgent:
    def __init__(self):
        self.name = "Writer"
        self.role = "Creates content from research"

    def execute(self, task: str) -> str:
        return f"[Writer] Generated report from: {task}"

class ReviewerAgent:
    def __init__(self):
        self.name = "Reviewer"
        self.role = "Quality checks and fact-checking"

    def execute(self, task: str) -> str:
        return f"[Reviewer] Verified: {task} — 0 errors found"

class MultiAgentOrchestrator:
    def __init__(self):
        self.agents: dict[str, Agent] = {}

    def register(self, agent: Agent):
        self.agents[agent.name.lower()] = agent

    def run(self, task: str, pipeline: list[str]):
        result = task
        for agent_name in pipeline:
            agent = self.agents.get(agent_name.lower())
            if not agent:
                raise ValueError(f"Agent not found: {agent_name}")
            result = agent.execute(result)
            print(f"  → {agent.name}: Done")
        return result

orchestrator = MultiAgentOrchestrator()
orchestrator.register(ResearcherAgent())
orchestrator.register(WriterAgent())
orchestrator.register(ReviewerAgent())

final = orchestrator.run("AI security trends 2026",
                          pipeline=["researcher", "writer", "reviewer"])
print(f"\nFinal output:\n{final}")
