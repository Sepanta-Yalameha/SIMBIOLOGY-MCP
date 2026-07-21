"""SABIO-RK kinetics API wrapper (new open export API, no key required)."""

from __future__ import annotations

from typing import Any
import json

import httpx

_SABIO_BASE = "https://sabiork.h-its.org/export-api/sabio/kinlaw-entry/json"


def _get(url: str, params: dict[str, Any]) -> str:
    try:
        response = httpx.get(url, params=params, timeout=60.0, follow_redirects=True)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise RuntimeError(f"SABIO-RK request failed: {exc}") from exc
    return response.text


def _load(text: str, url: str) -> Any:
    try:
        return json.loads(text)
    except (ValueError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"SABIO-RK returned a non-JSON response; the API endpoint may have changed: {url}") from exc


def _dict(value: Any) -> dict[str, Any]:
    """Coerce a value to a dict at the extraction boundary (missing/None/non-dict -> {})."""

    return value if isinstance(value, dict) else {}


def _entries(payload: Any) -> list[dict[str, Any]]:
    """Normalize a kinlaw payload to a list of entry dicts.

    Handles the search envelope ({"data": [...]}), a single-entry envelope
    ({"data": {...}}), and a bare entry dict, so search() and entry() share one
    model of the response shape.
    """

    if isinstance(payload, dict) and "data" in payload:
        payload = payload.get("data")
    if isinstance(payload, dict):
        return [payload]
    if isinstance(payload, list):
        return [entry for entry in payload if isinstance(entry, dict)]
    return []


def _slim_parameter(param: Any) -> dict[str, Any]:
    param = _dict(param)
    parameter_type = _dict(param.get("parameter_type"))
    species = _dict(param.get("species"))
    unit = _dict(param.get("unit"))
    return {
        "name": param.get("name"),
        "type": parameter_type.get("name"),
        "species": species.get("species_key"),
        "start_value": param.get("start_value"),
        "end_value": param.get("end_value"),
        "standard_deviation": param.get("standard_deviation"),
        "unit": unit.get("name"),
        "normalized_value": param.get("n_start_value"),
        "normalized_unit": unit.get("n_name"),
    }


def _slim(entry: Any) -> dict[str, Any]:
    entry = _dict(entry)
    general = _dict(entry.get("general"))
    organism = _dict(general.get("organism"))
    reaction = _dict(entry.get("reaction"))
    kineticlaw = _dict(entry.get("kineticlaw"))
    kinlaw_type = _dict(kineticlaw.get("kinlaw_type"))
    enzyme = _dict(entry.get("enzyme_description"))
    conditions = _dict(entry.get("experimental_conditions"))
    envvar_ph = _dict(conditions.get("envvar_ph"))
    envvar_temperature = _dict(conditions.get("envvar_temperature"))
    publication = _dict(entry.get("publication"))

    raw_parameters = kineticlaw.get("parameter")
    if isinstance(raw_parameters, dict):
        raw_parameters = [raw_parameters]  # a lone parameter may serialize as an object, not a 1-element list
    elif not isinstance(raw_parameters, list):
        raw_parameters = []

    return {
        "entry_id": entry.get("id"),
        "organism": organism.get("name"),
        "experiment_type": general.get("experiment_type"),
        "mechanism": general.get("mechanism"),
        "reaction": reaction.get("equation"),
        "kinetic_law_type": kinlaw_type.get("name"),
        "reversible": kineticlaw.get("reversible"),
        "formula": kineticlaw.get("formula"),
        "parameters": [_slim_parameter(p) for p in raw_parameters],
        "ec_number": enzyme.get("ec_number"),
        "enzyme_name": enzyme.get("enzyme_name"),
        "conditions": {
            "ph": envvar_ph.get("start_value"),
            "temperature": envvar_temperature.get("start_value"),
            "temperature_unit": envvar_temperature.get("unit"),
            "buffer": conditions.get("buffer"),
        },
        "publication": {
            "pubmed_id": publication.get("pubmed_id"),
            "title": publication.get("title"),
            "author": publication.get("author"),
            "journal": publication.get("journal"),
            "year": publication.get("year"),
        },
    }


def _build_query(
    query: str = "",
    organism: str | None = None,
    substrate: str | None = None,
    ec_number: str | None = None,
    parameter_type: str | None = None,
) -> str:
    clauses: list[str] = []
    if query and query.strip():
        clauses.append(query.strip())
    if organism:
        clauses.append(f'Organism:"{organism}"')
    if substrate:
        clauses.append(f'Substrate:"{substrate}"')
    if ec_number:
        clauses.append(f'ECNumber:"{ec_number}"')
    if parameter_type:
        clauses.append(f'Parametertype:"{parameter_type}"')

    if not clauses:
        raise ValueError("Provide a query or at least one filter (organism, substrate, ec_number, parameter_type).")

    return " AND ".join(clauses)


def search(
    query: str = "",
    limit: int = 10,
    organism: str | None = None,
    substrate: str | None = None,
    ec_number: str | None = None,
    parameter_type: str | None = None,
) -> dict[str, Any]:
    """Search SABIO-RK for enzyme kinetics entries and return slimmed records."""

    effective_q = _build_query(query, organism, substrate, ec_number, parameter_type)
    page_size = max(1, min(int(limit), 50))

    params = {"q": effective_q, "page": 1, "pageSize": page_size}
    payload = _load(_get(_SABIO_BASE, params), _SABIO_BASE)
    meta = _dict(_dict(payload).get("meta"))
    results = [_slim(entry) for entry in _entries(payload)]

    return {
        "query": effective_q,
        "total_count": meta.get("total_count"),
        "count": len(results),
        "results": results,
    }


def entry(entry_id: int) -> dict[str, Any]:
    """Fetch a single SABIO-RK kinetics entry by id and return a slimmed record."""

    url = f"{_SABIO_BASE}/{entry_id}"
    payload = _load(_get(url, {}), url)
    entries = _entries(payload)
    return _slim(entries[0]) if entries else _slim({})
