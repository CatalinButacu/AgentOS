from __future__ import annotations

from agentos.agents.base import Agent
from agentos.domain.compliance import Claim
from agentos.infra.model_router import ModelRouter
from agentos.infra.tool_gateway import ToolGateway
from agentos.knowledge.retrieval import GraphRAGRetriever


class RetrieverAgent(Agent):
    def __init__(self, name: str, models: ModelRouter, tools: ToolGateway,
                 retriever: GraphRAGRetriever) -> None:
        super().__init__(name, models, tools)
        self.retriever = retriever

    def gather_evidence(self, claim: Claim, token_budget: int) -> list[str]:
        query_vector = self.models.embed(claim.text)
        return self.retriever.retrieve(claim.text, token_budget, query_vector)
