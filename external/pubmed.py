"""PubMed API wrapper."""

from __future__ import annotations

import os
from typing import Any
import xml.etree.ElementTree as ET

import httpx

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional dependency path
    load_dotenv = None

_NCBI_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

if load_dotenv is not None:
    load_dotenv()


def _get(url: str, params: dict[str, Any] | None = None) -> httpx.Response:
    response = httpx.get(url, params=params, timeout=20.0, follow_redirects=True)
    response.raise_for_status()
    return response


def search(query: str, limit: int = 10) -> dict[str, Any]:
    api_key = os.getenv("NCBI_API_KEY")
    params: dict[str, Any] = {
        "db": "pubmed",
        "term": query,
        "retmode": "xml",
        "retmax": limit,
    }
    if api_key:
        params["api_key"] = api_key
    root = ET.fromstring(_get(f"{_NCBI_BASE}/esearch.fcgi", params).text)
    return {
        "count": int(root.findtext("Count", default="0")),
        "ids": [elem.text for elem in root.findall("./IdList/Id") if elem.text],
    }


def summary(pmid: str) -> dict[str, Any]:
    api_key = os.getenv("NCBI_API_KEY")
    params: dict[str, Any] = {
        "db": "pubmed",
        "id": pmid,
        "retmode": "xml",
    }
    if api_key:
        params["api_key"] = api_key
    root = ET.fromstring(_get(f"{_NCBI_BASE}/esummary.fcgi", params).text)
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
    api_key = os.getenv("NCBI_API_KEY")
    params: dict[str, Any] = {
        "db": "pubmed",
        "id": pmid,
        "retmode": "xml",
    }
    if api_key:
        params["api_key"] = api_key
    root = ET.fromstring(_get(f"{_NCBI_BASE}/efetch.fcgi", params).text)
    pubmed_article = root.find(".//PubmedArticle")
    if pubmed_article is None:
        return {}
    return {
        "pmid": pubmed_article.findtext(".//PMID", default=pmid),
        "title": pubmed_article.findtext(".//ArticleTitle", default=""),
        "abstract": " ".join(
            part.text or "" for part in pubmed_article.findall(".//Abstract/AbstractText")
        ).strip(),
        "journal": pubmed_article.findtext(".//Journal/Title", default=""),
    }
