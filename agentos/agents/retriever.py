from __future__ import annotations

from agentos.agents.base import Agent
from agentos.domain.compliance import Claim
from agentos.infra.model_router import ModelRouter
from agentos.infra.tool_gateway import Tool, ToolGateway
from agentos.knowledge.retrieval import GraphRAGRetriever


class RetrieverAgent(Agent):
    def __init__(self, name: str, models: ModelRouter, tools: ToolGateway,
                 retriever: GraphRAGRetriever) -> None:
        super().__init__(name, models, tools)
        self.retriever = retriever
        tools.register(Tool("retrieve_evidence",
                            "Retrieve evidence span ids for a query under a token budget",
                            retriever.retrieve, ("query_text", "token_budget", "query_vector")))

    def gather_evidence(self, claim: Claim, token_budget: int) -> list[str]:
        query_vector = self.models.embed(claim.text)
        call = self.tools.call("retrieve_evidence",
                               {"query_text": claim.text, "token_budget": token_budget,
                                "query_vector": query_vector})
        return call.result if call.ok else []
