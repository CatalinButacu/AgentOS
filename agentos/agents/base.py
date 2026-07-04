from __future__ import annotations

from agentos.infra.model_router import ModelRouter
from agentos.infra.tool_gateway import ToolGateway


class Agent:
    def __init__(self, name: str, models: ModelRouter, tools: ToolGateway) -> None:
        self.name = name
        self.models = models
        self.tools = tools
