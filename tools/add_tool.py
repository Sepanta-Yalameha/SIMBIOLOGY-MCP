"""Add two integers."""

from __future__ import annotations

from tools.registry import register
from tools.tool import BaseTool


@register("add")
class AddTool(BaseTool):
    """Return the sum of two integers."""

    def __init__(self, num1: int, num2: int) -> None:
        self.num1 = num1
        self.num2 = num2

    def run(self) -> int:
        """Return the sum of the configured operands."""

        return self.num1 + self.num2
