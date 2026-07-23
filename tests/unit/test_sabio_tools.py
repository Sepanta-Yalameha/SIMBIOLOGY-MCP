from __future__ import annotations

import json

import pytest

import simbiology_mcp.external.sabio as sabio
from simbiology_mcp.tools.external_tools import sabio_entry, sabio_search
from simbiology_mcp.tools.registry import TOOLS


def _entry() -> dict:
    return {
        "id": 12345,
        "lineage": {"junk": "should be dropped"},
        "external_links": ["also dropped"],
        "general": {
            "organism": {"name": "Escherichia coli"},
            "experiment_type": "assay",
            "mechanism": "Michaelis-Menten",
        },
        "reaction": {"equation": "ATP + glucose -> ADP + glucose-6-phosphate"},
        "kineticlaw": {
            "kinlaw_type": {"name": "Michaelis-Menten"},
            "reversible": False,
            "formula": "Vmax*S/(Km+S)",
            "parameter": [
                {
                    "name": "Km",
                    "parameter_type": {"name": "Km"},
                    "species": {"species_key": "ATP"},
                    "start_value": 5.0,
                    "end_value": None,
                    "standard_deviation": 0.2,
                    "unit": {"name": "µM", "n_name": "M"},
                    "n_start_value": 5e-6,
                }
            ],
        },
        "enzyme_description": {"ec_number": "2.7.1.2", "enzyme_name": "glucokinase"},
        "experimental_conditions": {
            "envvar_ph": {"start_value": 7.4},
            "envvar_temperature": {"start_value": 37.0, "unit": "°C"},
            "buffer": "Tris-HCl",
        },
        "publication": {
            "pubmed_id": "26840071",
            "title": "Kinetics of glucokinase",
            "author": "Doe J",
            "journal": "J Kinetics",
            "year": "2016",
        },
    }


def _search_json(total: int, entries: list) -> str:
    return json.dumps({"meta": {"page": 1, "page_size": 10, "total_count": total, "total_pages": 1}, "data": entries})


def test_sabio_tools_registered() -> None:
    assert "sabio_search" in TOOLS
    assert "sabio_entry" in TOOLS
    assert TOOLS["sabio_search"] is sabio_search
    assert TOOLS["sabio_entry"] is sabio_entry


def test_sabio_search_slims_and_extracts(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sabio, "_get", lambda url, params: _search_json(1, [_entry()]))

    result = sabio_search(substrate="ATP")

    assert result["total_count"] == 1
    assert result["count"] == 1
    entry = result["results"][0]

    assert "lineage" not in entry
    assert "external_links" not in entry
    assert entry["entry_id"] == 12345
    assert entry["organism"] == "Escherichia coli"
    assert entry["reaction"] == "ATP + glucose -> ADP + glucose-6-phosphate"
    assert entry["ec_number"] == "2.7.1.2"

    param = entry["parameters"][0]
    assert param["name"] == "Km"
    assert param["type"] == "Km"
    assert param["species"] == "ATP"
    assert param["start_value"] == 5.0
    assert param["unit"] == "µM"
    assert param["normalized_value"] == 5e-6
    assert param["normalized_unit"] == "M"

    assert entry["conditions"]["ph"] == 7.4
    assert entry["conditions"]["temperature"] == 37.0
    assert entry["publication"]["pubmed_id"] == "26840071"


def test_sabio_search_empty_results(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sabio, "_get", lambda url, params: _search_json(0, []))

    result = sabio_search(query="nonsense")

    assert result["total_count"] == 0
    assert result["results"] == []
    assert result["count"] == 0


def test_sabio_search_query_building_ands_clauses(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict = {}

    def fake_get(url: str, params: dict) -> str:
        captured.update(params)
        return _search_json(0, [])

    monkeypatch.setattr(sabio, "_get", fake_get)

    sabio_search(organism="Escherichia coli", substrate="ATP")

    q = captured["q"]
    assert 'Organism:"Escherichia coli"' in q
    assert 'Substrate:"ATP"' in q
    assert " AND " in q


def test_sabio_search_no_args_raises() -> None:
    with pytest.raises(ValueError, match="Provide a query"):
        sabio_search()


def test_sabio_entry_unwraps_and_slims(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sabio, "_get", lambda url, params: json.dumps(_entry()))

    result = sabio_entry(12345)

    assert result["entry_id"] == 12345
    assert result["parameters"][0]["normalized_unit"] == "M"
    assert "lineage" not in result


def test_sabio_entry_unwraps_data_list(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sabio, "_get", lambda url, params: json.dumps({"meta": {}, "data": [_entry()]}))

    result = sabio_entry(12345)

    assert result["entry_id"] == 12345
    assert result["parameters"][0]["type"] == "Km"


def test_sabio_entry_unwraps_data_dict(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sabio, "_get", lambda url, params: json.dumps({"data": _entry()}))

    result = sabio_entry(12345)

    assert result["entry_id"] == 12345


def test_sabio_search_parameter_as_dict(monkeypatch: pytest.MonkeyPatch) -> None:
    entry = _entry()
    entry["kineticlaw"]["parameter"] = entry["kineticlaw"]["parameter"][0]  # a lone object, not a list
    monkeypatch.setattr(sabio, "_get", lambda url, params: _search_json(1, [entry]))

    result = sabio_search(substrate="ATP")

    params = result["results"][0]["parameters"]
    assert len(params) == 1
    assert params[0]["type"] == "Km"


def test_sabio_search_quotes_parameter_type(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict = {}

    def fake_get(url: str, params: dict) -> str:
        captured.update(params)
        return _search_json(0, [])

    monkeypatch.setattr(sabio, "_get", fake_get)

    sabio_search(parameter_type="specific activity")

    assert 'Parametertype:"specific activity"' in captured["q"]
