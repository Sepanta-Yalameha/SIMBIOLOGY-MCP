import pytest

from tools.external_tools import pubmed_search


def test_pubmed_search_url_building(monkeypatch):
    captured = {}

    class DummyResponse:
        text = "<eSearchResult><Count>1</Count><IdList><Id>123</Id></IdList></eSearchResult>"

        def raise_for_status(self):
            return None

    def fake_get(url, params=None, timeout=None, follow_redirects=None):
        captured["url"] = url
        captured["params"] = params
        return DummyResponse()

    monkeypatch.setattr("httpx.get", fake_get)

    result = pubmed_search("cancer", limit=1)
    assert captured["url"].endswith("/esearch.fcgi")
    assert captured["params"]["db"] == "pubmed"
    assert result == {"count": 1, "ids": ["123"]}


@pytest.mark.live_external
def test_pubmed_search_live():
    result = pubmed_search("cancer", limit=1)
    assert result["count"] >= 1
    assert result["ids"]
