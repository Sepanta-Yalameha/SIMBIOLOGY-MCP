"""Tool registry for FastMCP registration."""

from __future__ import annotations
from tools.tool import BaseTool

TOOLS: dict[str, type[BaseTool]] = {}


def register(name: str):
    """Register a tool class under a FastMCP tool name."""

    def decorator(tool_cls: type[BaseTool]) -> type[BaseTool]:
        TOOLS[name] = tool_cls
        return tool_cls

    return decorator
