"""MCP tools wrapping external biological data APIs."""

from __future__ import annotations

from typing import Any

from external import igem, pubmed
from tools.registry import register


@register("pubmed_search")
def pubmed_search(query: str, limit: int = 10) -> dict[str, Any]:
    """Search PubMed for matching articles."""
    return pubmed.search(query, limit=limit)


@register("pubmed_summary")
def pubmed_summary(pmid: str) -> dict[str, Any]:
    """Fetch a PubMed article summary."""
    return pubmed.summary(pmid)


@register("pubmed_article")
def pubmed_article(pmid: str) -> dict[str, Any]:
    """Fetch full PubMed article metadata."""
    return pubmed.article(pmid)


@register("igem_part")
def igem_part(part_name: str) -> dict[str, Any]:
    """Fetch an iGEM part record by registry slug or exact part ID."""
    return igem.part(part_name)


@register("igem_search")
def igem_search(query: str, limit: int = 10) -> dict[str, Any]:
    """Search iGEM parts by free text."""
    return igem.search(query, limit=limit)


@register("igem_search_best")
def igem_search_best(query: str) -> dict[str, Any]:
    """Search iGEM parts and fetch the best matching part record."""
    return igem.search_best(query)
