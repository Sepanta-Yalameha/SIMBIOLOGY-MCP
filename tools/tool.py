"""Base tool abstractions for the SimBiology MCP server."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseTool(ABC):
    """Abstract base class for tools.

    Concrete tools should expose a normal ``__init__`` signature for the
    arguments FastMCP will bind and implement :meth:`run`.
    """

    @abstractmethod
    def __init__(self, *args: Any, **kwargs: Any) -> None:\
        raise TypeError("BaseTool cannot be instantiated directly.")

    @abstractmethod
    def run(self) -> Any:
        """Execute the tool."""
