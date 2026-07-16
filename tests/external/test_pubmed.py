import pytest

from simbiology_mcp.external.pubmed import search as pubmed_search

pytestmark = pytest.mark.live


def test_pubmed_search_live():
    result = pubmed_search("cancer", limit=1)
    assert result["count"] >= 1
    assert result["ids"]

