"""PubMed API wrapper."""

from __future__ import annotations

from pathlib import Path
from typing import Any
import os
import xml.etree.ElementTree as ET

import httpx
from dotenv import load_dotenv

_NCBI_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
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
