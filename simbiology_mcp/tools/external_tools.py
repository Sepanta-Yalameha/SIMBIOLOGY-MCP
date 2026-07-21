"""MCP tools wrapping external biological data APIs."""

from __future__ import annotations

from typing import Any

from ..external import igem, pubmed, sabio
from .registry import register


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


@register("pubmed_fulltext")
def pubmed_fulltext(
    pmid: str,
    sections: list[str] | None = None,
    include_references: bool = False,
    max_chars: int | None = None,
) -> dict[str, Any]:
    """Fetch section-labeled open-access full text for a PubMed article from PubMed Central.

    Returns full text grouped by section (TITLE, ABSTRACT, INTRO, METHODS, RESULTS, FIG,
    TABLE, DISCUSS, SUPPL). Methods, Results, and Tables are where kinetic constants and
    experimental parameters usually live. References are excluded unless ``include_references``
    is set. Use ``sections`` to filter (case-insensitive) and ``max_chars`` to cap size.
    When the paper is not open access, ``full_text_available`` is False and the response
    falls back to the PubMed abstract.
    """
    return pubmed.fulltext(pmid, sections=sections, include_references=include_references, max_chars=max_chars)


@register("sabio_search")
def sabio_search(
    query: str = "",
    limit: int = 10,
    organism: str | None = None,
    substrate: str | None = None,
    ec_number: str | None = None,
    parameter_type: str | None = None,
) -> dict[str, Any]:
    """Search SABIO-RK for measured enzyme kinetics (Km, kcat, Vmax, Ki, and more).

    Filter with the dedicated arguments (``organism``, ``substrate``, ``ec_number``,
    ``parameter_type``) or pass a raw fielded ``query`` using SABIO-RK syntax:
    ``Organism:"..."``, ``Substrate:"..."``, ``ECNumber:"..."``, ``Parametertype:...``,
    plus ``Pathway:...``, ``KeggReactionID:...``, and ``PubMedID:...``. Clauses combine with
    AND. Each returned parameter carries both the as-reported value/unit and an SI-normalized
    value/unit, and ``publication.pubmed_id`` cross-references PubMed and ``pubmed_fulltext``.
    """
    return sabio.search(
        query=query,
        limit=limit,
        organism=organism,
        substrate=substrate,
        ec_number=ec_number,
        parameter_type=parameter_type,
    )


@register("sabio_entry")
def sabio_entry(entry_id: int) -> dict[str, Any]:
    """Fetch a single SABIO-RK kinetics entry by its numeric id.

    Returns the slimmed entry: reaction, kinetic law, parameters (with both as-reported and
    SI-normalized values), enzyme/EC number, experimental conditions (pH, temperature, buffer),
    and the source publication, whose ``pubmed_id`` cross-references PubMed and ``pubmed_fulltext``.
    """
    return sabio.entry(entry_id)


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
