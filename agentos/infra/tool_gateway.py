from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    handler: Callable[..., Any]
    parameters: tuple[str, ...] = ()


@dataclass(frozen=True)
class ToolCall:
    name: str
    arguments: dict
    ok: bool
    result: Any = None
    error: str | None = None


class ToolGateway:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}
        self._log: list[ToolCall] = []

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def describe(self) -> list[dict]:
        return [{"name": tool.name, "description": tool.description,
                 "parameters": list(tool.parameters)}
                for tool in self._tools.values()]

    def call(self, name: str, arguments: dict | None = None) -> ToolCall:
        arguments = arguments or {}
        tool = self._tools.get(name)
        if tool is None:
            return self._record(ToolCall(name, arguments, False, error="unknown tool"))
        missing = [parameter for parameter in tool.parameters if parameter not in arguments]
        if missing:
            return self._record(ToolCall(name, arguments, False,
                                         error=f"missing arguments: {', '.join(missing)}"))
        try:
            result = tool.handler(**arguments)
        except Exception as error:
            return self._record(ToolCall(name, arguments, False, error=str(error)))
        return self._record(ToolCall(name, arguments, True, result=result))

    @property
    def calls(self) -> list[ToolCall]:
        return list(self._log)

    def _record(self, call: ToolCall) -> ToolCall:
        self._log.append(call)
        return call
