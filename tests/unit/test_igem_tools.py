from __future__ import annotations

from typing import Any

import pytest

import simbiology_mcp.external.igem as igem
from simbiology_mcp.tools.external_tools import igem_part, igem_search, igem_search_best
from simbiology_mcp.tools.registry import TOOLS


def test_igem_search_is_registered() -> None:
    assert "igem_search" in TOOLS
    assert TOOLS["igem_search"] is igem_search


def test_igem_search_best_is_registered() -> None:
    assert "igem_search_best" in TOOLS
    assert TOOLS["igem_search_best"] is igem_search_best


def test_igem_part_rejects_free_text() -> None:
    with pytest.raises(ValueError, match="use igem_search"):
        igem_part("lacI coding sequence")


def test_igem_client_failure_is_reported_gracefully(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeClient:
        def connect(self) -> None:
            raise RuntimeError("boom")

    monkeypatch.setattr(igem, "Client", FakeClient)
    igem._client.cache_clear()

    with pytest.raises(igem.IgemUnavailableError, match="Could not connect to the iGEM registry"):
        igem.part("BBa_J23100")


def test_health_status_tolerates_unknown_components() -> None:
    """A health component the client has never heard of must not break parsing.

    The registry gains components over time: adding `valkey` was enough to fail
    every connect() while the registry itself reported "ok", because the client
    ships these models with extra="forbid". The payload below is the real
    response that broke it.
    """
    from igem_registry_api.client import HealthStatus

    igem._relax_response_models()

    component = {"database": {"status": "up"}, "memory_rss": {"status": "up"}, "valkey": {"status": "up"}}
    parsed = HealthStatus.model_validate({"status": "ok", "info": component, "error": {}, "details": component})

    assert parsed.status == "ok"


def test_relax_stays_inside_the_registry_client() -> None:
    """The sweep must not escape igem_registry_api into pydantic itself.

    The client imports pydantic's base classes into its own namespace, so
    selecting models by shape alone also caught BaseModel and RootModel.
    Relaxing those reaches every model in the process rather than this client's:
    unrelated models start retaining unknown fields, and RootModel refuses the
    change outright, so any RootModel subclass built afterwards raises
    PydanticUserError.
    """
    from pydantic import BaseModel, RootModel

    igem._relax_response_models()

    class Unrelated(BaseModel):
        kept: int

    # Stock pydantic drops an unknown field; a leaked extra="allow" would keep it.
    assert Unrelated.model_validate({"kept": 1, "unknown": 2}).model_dump() == {"kept": 1}

    class Rooted(RootModel[int]):
        pass

    assert Rooted.model_validate(3).root == 3


def test_igem_part_fetches_by_slug(monkeypatch: pytest.MonkeyPatch) -> None:
    client = object()
    calls: list[Any] = []

    def fake_get(fake_client: Any, ref: Any) -> dict[str, Any]:
        calls.append((fake_client, ref))
        assert fake_client is client
        assert ref.slug == "bba-j23100"
        return {
            "name": "BBa_J23100",
            "slug": "bba-j23100",
            "uuid": "uuid-1",
            "title": "Constitutive promoter",
            "description": "demo",
            "status": "published",
            "source": "https://example.invalid",
            "sequence": "ATGC",
            "audit": {"created": "2026-01-01T00:00:00Z", "updated": "2026-01-02T00:00:00Z"},
            "license": {"uuid": "license-1"},
        }

    monkeypatch.setattr(igem, "_client", lambda: client)
    monkeypatch.setattr(igem.Part, "get", fake_get)

    result = igem_part("BBa_J23100")

    assert result["part"] == "BBa_J23100"
    assert result["slug"] == "bba-j23100"
    assert result["uuid"] == "uuid-1"
    assert result["title"] == "Constitutive promoter"
    assert result["license_uuid"] == "license-1"
    assert result["created"] == "2026-01-01T00:00:00+00:00"
    assert calls


def test_igem_search_returns_summaries(monkeypatch: pytest.MonkeyPatch) -> None:
    client = object()

    def fake_search(fake_client: Any, query: str, *, limit: int) -> list[dict[str, Any]]:
        assert fake_client is client
        assert query == "lacI"
        assert limit == 2
        return [
            {
                "name": "BBa_J23100",
                "slug": "bba-j23100",
                "uuid": "uuid-1",
                "title": "Constitutive promoter",
                "description": "demo",
                "status": "published",
                "audit": {"updated": "2026-01-02T00:00:00Z"},
            }
        ]

    monkeypatch.setattr(igem, "_client", lambda: client)
    monkeypatch.setattr(igem.Part, "search", fake_search)

    result = igem_search("lacI", limit=2)

    assert result == {
        "query": "lacI",
        "count": 1,
        "results": [
            {
                "name": "BBa_J23100",
                "slug": "bba-j23100",
                "uuid": "uuid-1",
                "title": "Constitutive promoter",
                "description": "demo",
                "status": "published",
                "role": {"uuid": "", "accession": "", "label": "", "deprecated": False},
                "updated": "2026-01-02T00:00:00+00:00",
            }
        ],
    }


def test_igem_search_best_returns_selected_and_alternatives(monkeypatch: pytest.MonkeyPatch) -> None:
    client = object()

    def fake_search(fake_client: Any, query: str, *, limit: int) -> list[dict[str, Any]]:
        assert fake_client is client
        assert query == "lacI"
        assert limit == 5
        return [
            {
                "name": "BBa_J23100",
                "slug": "bba-j23100",
                "uuid": "uuid-1",
                "title": "Constitutive promoter",
                "description": "demo",
                "status": "published",
                "audit": {"updated": "2026-01-02T00:00:00Z"},
            },
            {
                "name": "BBa_J23101",
                "slug": "bba-j23101",
                "uuid": "uuid-2",
                "title": "Variant promoter",
                "description": "alt",
                "status": "published",
                "audit": {"updated": "2026-01-03T00:00:00Z"},
            },
        ]

    monkeypatch.setattr(igem, "_client", lambda: client)
    monkeypatch.setattr(igem.Part, "search", fake_search)

    result = igem_search_best("lacI")

    assert result["query"] == "lacI"
    assert result["selected"]["part"] == "BBa_J23100"
    assert result["selected"]["uuid"] == "uuid-1"
    assert result["selected"]["updated"] == "2026-01-02T00:00:00+00:00"
    assert result["alternatives"] == [
        {
            "name": "BBa_J23101",
            "slug": "bba-j23101",
            "uuid": "uuid-2",
            "title": "Variant promoter",
            "description": "alt",
            "status": "published",
            "role": {"uuid": "", "accession": "", "label": "", "deprecated": False},
            "updated": "2026-01-03T00:00:00+00:00",
        }
    ]

