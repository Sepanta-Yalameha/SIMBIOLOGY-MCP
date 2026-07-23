from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

import simbiology_mcp.external.pubmed as pubmed
from simbiology_mcp.tools.external_tools import pubmed_fulltext
from simbiology_mcp.tools.registry import TOOLS


def _bioc_json() -> str:
    document = {
        "id": "PMC4739585",
        "infons": {"license": "CC BY"},
        "passages": [
            {
                "infons": {
                    "section_type": "TITLE",
                    "type": "front",
                    "article-id_pmid": "26840071",
                    "article-id_pmc": "PMC4739585",
                    "article-id_doi": "10.1000/demo.doi",
                    "title": "A demo open access article",
                    "journal": "Journal of Demos",
                    "year": "2016",
                },
                "text": "A demo open access article",
            },
            {
                "infons": {"section_type": "METHODS", "type": "paragraph"},
                "text": "We measured the rate constant k using assay X.",
            },
            {
                "infons": {"section_type": "RESULTS", "type": "paragraph"},
                "text": "The measured Km was 5 uM at 37 C.",
            },
            {
                "infons": {"section_type": "REF", "type": "ref"},
                "text": "Smith et al. 2010.",
            },
        ],
    }
    return json.dumps([{"documents": [document]}])


def _fake_article(pmid: str) -> dict[str, Any]:
    return {"pmid": pmid, "title": "Paywalled paper", "abstract": "Only the abstract is public.", "journal": "Closed Journal"}


def test_pubmed_fulltext_is_registered() -> None:
    assert "pubmed_fulltext" in TOOLS
    assert TOOLS["pubmed_fulltext"] is pubmed_fulltext


def test_pubmed_fulltext_excludes_references_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pubmed, "_get", lambda url, params: _bioc_json())

    result = pubmed_fulltext("26840071")

    assert result["full_text_available"] is True
    assert result["pmcid"] == "PMC4739585"
    assert result["doi"] == "10.1000/demo.doi"
    assert result["title"] == "A demo open access article"
    assert result["journal"] == "Journal of Demos"
    assert result["license"] == "CC BY"
    assert result["available_sections"] == ["TITLE", "METHODS", "RESULTS", "REF"]
    sections = {s["section"] for s in result["sections"]}
    assert "REF" not in sections
    assert "METHODS" in sections and "RESULTS" in sections
    assert result["truncated"] is False


def test_pubmed_fulltext_include_references(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pubmed, "_get", lambda url, params: _bioc_json())

    result = pubmed_fulltext("26840071", include_references=True)

    sections = {s["section"] for s in result["sections"]}
    assert "REF" in sections


def test_pubmed_fulltext_section_filter_is_case_insensitive(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pubmed, "_get", lambda url, params: _bioc_json())

    result = pubmed_fulltext("26840071", sections=["methods"])

    assert [s["section"] for s in result["sections"]] == ["METHODS"]
    assert result["sections"][0]["text"] == "We measured the rate constant k using assay X."


def test_pubmed_fulltext_max_chars_truncates(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pubmed, "_get", lambda url, params: _bioc_json())

    result = pubmed_fulltext("26840071", max_chars=10)

    assert result["truncated"] is True
    total = sum(len(s["text"]) for s in result["sections"])
    assert total <= 10


def test_pubmed_fulltext_no_open_access_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pubmed, "_get", lambda url, params: "[Error] : No result can be found. Please check ...")
    monkeypatch.setattr(pubmed, "article", _fake_article)

    result = pubmed_fulltext("12345")

    assert result["full_text_available"] is False
    assert result["abstract"] == "Only the abstract is public."
    assert result["title"] == "Paywalled paper"
    assert result["journal"] == "Closed Journal"
    assert "paywalled" in result["reason"].lower()


def test_pubmed_fulltext_http_error_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(url: str, params: dict) -> str:
        raise httpx.ConnectError("network down")

    monkeypatch.setattr(pubmed, "_get", boom)
    monkeypatch.setattr(pubmed, "article", _fake_article)

    result = pubmed_fulltext("26840071")

    assert result["full_text_available"] is False
    assert result["abstract"] == "Only the abstract is public."


def test_pubmed_fulltext_empty_document_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    empty = json.dumps([{"documents": [{"id": "PMC1", "infons": {}, "passages": []}]}])
    monkeypatch.setattr(pubmed, "_get", lambda url, params: empty)
    monkeypatch.setattr(pubmed, "article", _fake_article)

    result = pubmed_fulltext("26840071")

    assert result["full_text_available"] is False
    assert result["abstract"] == "Only the abstract is public."


def test_pubmed_fulltext_merges_non_consecutive_sections(monkeypatch: pytest.MonkeyPatch) -> None:
    document = {
        "id": "PMC2",
        "infons": {"license": "CC BY"},
        "passages": [
            {"infons": {"section_type": "TITLE", "article-id_pmid": "9", "title": "T", "journal": "J"}, "text": "T"},
            {"infons": {"section_type": "METHODS"}, "text": "methods part one"},
            {"infons": {"section_type": "FIG"}, "text": "figure caption"},
            {"infons": {"section_type": "METHODS"}, "text": "methods part two"},
        ],
    }
    monkeypatch.setattr(pubmed, "_get", lambda url, params: json.dumps([{"documents": [document]}]))

    result = pubmed_fulltext("9", sections=["methods"])

    methods = [s for s in result["sections"] if s["section"] == "METHODS"]
    assert len(methods) == 1
    assert methods[0]["text"] == "methods part one\nmethods part two"
    assert result["available_sections"].count("METHODS") == 1


def test_pubmed_fulltext_include_references_with_section_filter(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pubmed, "_get", lambda url, params: _bioc_json())

    result = pubmed_fulltext("26840071", sections=["methods"], include_references=True)

    sections = {s["section"] for s in result["sections"]}
    assert sections == {"METHODS", "REF"}


def test_pubmed_fulltext_max_chars_emits_no_empty_section(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pubmed, "_get", lambda url, params: _bioc_json())

    result = pubmed_fulltext("26840071", max_chars=5)

    assert result["truncated"] is True
    assert all(s["text"] for s in result["sections"])  # no zero-length section entries
    assert sum(len(s["text"]) for s in result["sections"]) <= 5


def test_pubmed_fulltext_max_chars_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pubmed, "_get", lambda url, params: _bioc_json())

    result = pubmed_fulltext("26840071", max_chars=0)

    assert result["sections"] == []
    assert result["truncated"] is True
