import pytest

from tools.external_tools import igem_part


def test_igem_part_url_building(monkeypatch):
    captured = {}

    class DummyResponse:
        text = '{"title":"Part BBa_K0001"}'

        def raise_for_status(self):
            return None

        def json(self):
            return {"title": "Part BBa_K0001"}

    def fake_get(self, url, timeout=None):
        captured["url"] = url
        captured["timeout"] = timeout
        return DummyResponse()

    monkeypatch.setattr("external.igem.requests.Session.get", fake_get)

    result = igem_part("BBa_K0001")
    assert captured["url"].endswith("/parts/slugs/bba-k0001")
    assert captured["timeout"] == 30.0
    assert result["part"] == "BBa_K0001"
    assert result["title"] == "Part BBa_K0001"
    assert result["content"] == '{"title":"Part BBa_K0001"}'


@pytest.mark.live_external
def test_igem_part_live():
    result = igem_part("BBa_J23100")
    assert result["part"] == "BBa_J23100"
    assert result["url"].endswith("/parts/bba-j23100")
    assert result["title"]
