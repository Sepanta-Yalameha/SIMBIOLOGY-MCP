"""PubMed API wrapper."""

from __future__ import annotations

from pathlib import Path
from typing import Any
import json
import os
import xml.etree.ElementTree as ET

import httpx
from dotenv import load_dotenv

_NCBI_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
_BIOC_BASE = "https://www.ncbi.nlm.nih.gov/research/bionlp/RESTful/pmcoa.cgi/BioC_json"
_ENV_PATH = Path(__file__).resolve().parents[1] / ".env"

if _ENV_PATH.exists():
    load_dotenv(_ENV_PATH)


def _get(url: str, params: dict[str, Any]) -> str:
    response = httpx.get(url, params=params, timeout=20.0, follow_redirects=True)
    response.raise_for_status()
    return response.text


def _with_api_key(params: dict[str, Any]) -> dict[str, Any]:
    api_key = os.getenv("NCBI_API_KEY")
    if api_key:
        params["api_key"] = api_key
    return params


def search(query: str, limit: int = 10) -> dict[str, Any]:
    root = ET.fromstring(
        _get(
            f"{_NCBI_BASE}/esearch.fcgi",
            _with_api_key(
                {
                    "db": "pubmed",
                    "term": query,
                    "retmode": "xml",
                    "retmax": limit,
                }
            ),
        )
    )
    return {
        "count": int(root.findtext("Count", default="0")),
        "ids": [elem.text for elem in root.findall("./IdList/Id") if elem.text],
    }


def summary(pmid: str) -> dict[str, Any]:
    root = ET.fromstring(
        _get(
            f"{_NCBI_BASE}/esummary.fcgi",
            _with_api_key(
                {
                    "db": "pubmed",
                    "id": pmid,
                    "retmode": "xml",
                }
            ),
        )
    )
    doc = root.find("./DocSum")
    if doc is None:
        return {}
    result: dict[str, Any] = {"uid": doc.findtext("Id", default=pmid)}
    for item in doc.findall("Item"):
        name = item.attrib.get("Name")
        if name:
            result[name] = item.text
    return result


def article(pmid: str) -> dict[str, Any]:
    root = ET.fromstring(
        _get(
            f"{_NCBI_BASE}/efetch.fcgi",
            _with_api_key(
                {
                    "db": "pubmed",
                    "id": pmid,
                    "retmode": "xml",
                }
            ),
        )
    )
    pubmed_article = root.find(".//PubmedArticle")
    if pubmed_article is None:
        return {}
    return {
        "pmid": pubmed_article.findtext(".//PMID", default=pmid),
        "title": pubmed_article.findtext(".//ArticleTitle", default=""),
        "abstract": " ".join(part.text or "" for part in pubmed_article.findall(".//Abstract/AbstractText")).strip(),
        "journal": pubmed_article.findtext(".//Journal/Title", default=""),
    }


def _article_or_empty(pmid: str) -> dict[str, Any]:
    """Best-effort PubMed citation metadata; never raises so it can enrich a result."""

    try:
        return article(pmid)
    except Exception:  # noqa: BLE001 - metadata enrichment must never break the caller
        return {}


def _fulltext_fallback(pmid: str) -> dict[str, Any]:
    """Abstract-only response used when PMC has no open-access full text."""

    meta = _article_or_empty(pmid)
    return {
        "pmid": pmid,
        "full_text_available": False,
        "reason": "No open-access full text in PubMed Central (article is paywalled or not deposited in PMC).",
        "abstract": meta.get("abstract", ""),
        "title": meta.get("title", ""),
        "journal": meta.get("journal", ""),
    }


def fulltext(
    pmid: str,
    sections: list[str] | None = None,
    include_references: bool = False,
    max_chars: int | None = None,
) -> dict[str, Any]:
    """Fetch open-access full text for a PMID from PubMed Central via the BioC API.

    Returns full text grouped by section (all passages of one section_type merged, in
    first-seen order) when the article is open access, or falls back to the PubMed
    abstract with ``full_text_available`` False when it is not, including transient HTTP
    failures and documents that carry no readable passages.
    """

    try:
        raw = _get(f"{_BIOC_BASE}/{pmid}/unicode", {})
    except httpx.HTTPError:
        raw = ""
    text = raw.strip()

    document: dict[str, Any] | None = None
    if text and not text.startswith("[Error]"):
        try:
            payload = json.loads(text)
        except (ValueError, json.JSONDecodeError):
            payload = None
        if isinstance(payload, list) and payload:
            documents = (payload[0] or {}).get("documents") or []
            if documents:
                document = documents[0] or {}

    document = document or {}
    passages = document.get("passages") or []
    if not passages:
        return _fulltext_fallback(pmid)

    front_infons: dict[str, Any] = {}
    for passage in passages:
        infons = (passage or {}).get("infons") or {}
        if infons.get("article-id_pmid") or infons.get("article-id_pmc") or infons.get("title"):
            front_infons = infons
            break

    resolved_pmid = str(front_infons.get("article-id_pmid") or pmid)
    resolved_pmcid = str(front_infons.get("article-id_pmc") or document.get("id") or "")
    resolved_doi = str(front_infons.get("article-id_doi") or "")
    resolved_title = str(front_infons.get("title") or "")
    resolved_journal = str(front_infons.get("journal") or "")
    doc_infons = document.get("infons")
    resolved_license = str(doc_infons.get("license") or "") if isinstance(doc_infons, dict) else ""

    # BioC passages carry no journal name (and occasionally no title); backfill from the
    # PubMed citation, best effort, so the returned metadata is usable for a citation.
    if not resolved_journal or not resolved_title:
        meta = _article_or_empty(pmid)
        resolved_journal = resolved_journal or str(meta.get("journal") or "")
        resolved_title = resolved_title or str(meta.get("title") or "")

    # Merge every passage of the same section_type (not just consecutive runs); the dict
    # preserves first-seen order, so a section interleaved with figures stays a single block
    # instead of splitting into duplicate entries that collapse when a caller keys by name.
    texts_by_section: dict[str, list[str]] = {}
    for passage in passages:
        infons = (passage or {}).get("infons") or {}
        section_type = str(infons.get("section_type") or "")
        passage_text = str((passage or {}).get("text") or "")
        texts_by_section.setdefault(section_type, []).append(passage_text)

    available_sections = [section for section in texts_by_section if section]

    requested = [s.upper() for s in sections] if sections else None
    want_refs = include_references or bool(requested and "REF" in requested)

    selected: list[dict[str, str]] = []
    for section_type, parts in texts_by_section.items():
        if not section_type:
            continue
        if section_type == "REF":
            if not want_refs:
                continue
        elif requested is not None and section_type not in requested:
            continue
        joined = "\n".join(t for t in parts if t)
        selected.append({"section": section_type, "text": joined})

    truncated = False
    if max_chars is not None:
        capped: list[dict[str, str]] = []
        remaining = max(0, int(max_chars))
        for item in selected:
            if remaining <= 0:
                truncated = True
                break
            body = item["text"]
            if len(body) <= remaining:
                capped.append(item)
                remaining -= len(body)
            else:
                capped.append({"section": item["section"], "text": body[:remaining]})
                truncated = True
                break
        selected = capped

    return {
        "pmid": resolved_pmid,
        "pmcid": resolved_pmcid,
        "doi": resolved_doi,
        "license": resolved_license,
        "title": resolved_title,
        "journal": resolved_journal,
        "full_text_available": True,
        "available_sections": available_sections,
        "sections": selected,
        "truncated": truncated,
    }
