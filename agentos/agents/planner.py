from __future__ import annotations

from agentos.agents.base import Agent
from agentos.domain.compliance import Claim, ComplianceQuestion


class Planner(Agent):
    def decompose(self, question: ComplianceQuestion) -> list[Claim]:
        return [
            Claim(id=f"claim.{requirement.id}",
                  requirement_id=requirement.id,
                  text=requirement.text,
                  is_executable=requirement.check is not None,
                  check=requirement.check)
            for requirement in question.requirements
        ]
