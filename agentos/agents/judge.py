from __future__ import annotations

from agentos.agents.base import Agent
from agentos.domain.compliance import SupportLink
from agentos.domain.sources import EvidenceSpan


class JudgeAgent(Agent):
    def score_groundedness(self, support: SupportLink, evidence: list[EvidenceSpan]) -> float:
        return support.groundedness_score
