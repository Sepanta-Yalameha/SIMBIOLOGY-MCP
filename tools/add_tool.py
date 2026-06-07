"""Add two integers."""

from __future__ import annotations

from tools.registry import register


@register("add")
def add(num1: int, num2: int) -> int:
    """Return the sum of two integers."""

    return num1 + num2
