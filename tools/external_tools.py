"""MCP tools wrapping external biological data APIs."""

from __future__ import annotations

from typing import Any

from external import igem, pubmed
from tools.registry import register


@register("pubmed_search")
def pubmed_search(query: str, limit: int = 10, api_key: str | None = None) -> dict[str, Any]:
    return pubmed.search(query, limit=limit, api_key=api_key)


@register("pubmed_summary")
def pubmed_summary(pmid: str, api_key: str | None = None) -> dict[str, Any]:
    return pubmed.summary(pmid, api_key=api_key)


@register("pubmed_article")
def pubmed_article(pmid: str, api_key: str | None = None) -> dict[str, Any]:
    return pubmed.article(pmid, api_key=api_key)


@register("igem_part")
def igem_part(part_name: str) -> dict[str, Any]:
    return igem.part(part_name)
