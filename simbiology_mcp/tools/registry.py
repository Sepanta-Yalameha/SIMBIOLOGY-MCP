"""Shared tool registry for MCP and future CLI entrypoints."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

TOOLS: dict[str, Callable[..., Any]] = {}


def register(name: str):
    def decorator(tool_fn: Callable[..., Any]) -> Callable[..., Any]:
        TOOLS[name] = tool_fn
        return tool_fn

    return decorator
