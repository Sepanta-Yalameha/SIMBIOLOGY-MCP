import pytest

from simbiology_mcp.external.pubmed import fulltext as pubmed_fulltext
from simbiology_mcp.external.pubmed import search as pubmed_search

pytestmark = pytest.mark.live


def test_pubmed_search_live():
    result = pubmed_search("cancer", limit=1)
    assert result["count"] >= 1
    assert result["ids"]


def test_pubmed_fulltext_live():
    result = pubmed_fulltext("26840071")
    assert result["full_text_available"] is True
    sections = {s["section"]: s["text"] for s in result["sections"]}
    assert any(sections.get(name) for name in ("METHODS", "RESULTS"))

    missing = pubmed_fulltext("12345")
    assert missing["full_text_available"] is False

