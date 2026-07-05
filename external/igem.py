"""iGEM registry API wrapper."""

from __future__ import annotations

from functools import lru_cache
import re
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from igem_registry_api import Client, Part, Reference

_PART_SLUG_RE = re.compile(r"^(?:bba-[a-z0-9]{1,10}|psb[a-z0-9]{3,5})$")


@lru_cache(maxsize=1)
def _client() -> Client:
    client = Client()
    client.connect()
    return client


def _dump(obj: Any) -> dict[str, Any]:
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")
    if isinstance(obj, dict):
        return obj
    raise TypeError(f"Unsupported iGEM object type: {type(obj)!r}")


def _parse_iso_datetime(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc).isoformat()
    except ValueError:
        return value


def _role(role: dict[str, Any]) -> dict[str, Any]:
    return {
        "uuid": str(role.get("uuid") or ""),
        "accession": str(role.get("accession") or ""),
        "label": str(role.get("label") or ""),
        "deprecated": bool(role.get("deprecated")),
    }


def _normalize_part_slug(part_name: str) -> str:
    raw = part_name.strip().lower()
    if not raw:
        raise ValueError("part_name must not be empty")

    if raw.startswith("bba_") or raw.startswith("bba-"):
        slug = f"bba-{raw[4:].replace('_', '-')}"
    elif raw.startswith("psb_") or raw.startswith("psb-"):
        slug = f"psb{raw[4:].replace('_', '')}"
    else:
        slug = raw.replace("_", "-")

    if not _PART_SLUG_RE.fullmatch(slug):
        raise ValueError("part_name must be an exact iGEM part ID or slug like " "BBa_J23100, bba-j23100, pSB1C3, or psb1c3; " "use igem_search for free-text queries.")

    return slug


def _reference(part_name: str) -> Reference:
    raw = part_name.strip()
    if not raw:
        raise ValueError("part_name must not be empty")

    try:
        return Reference(uuid=str(UUID(raw)))
    except ValueError:
        return Reference(slug=_normalize_part_slug(raw))


def _normalize(part: Any) -> dict[str, Any]:
    data = _dump(part)
    audit = data.get("audit") or {}
    license_value = data.get("license") or data.get("licenseUUID") or ""
    license_uuid = str(license_value.get("uuid") or "") if isinstance(license_value, dict) else str(license_value or "")

    return {
        "part": str(data.get("name") or data.get("slug") or ""),
        "name": str(data.get("name") or ""),
        "slug": str(data.get("slug") or ""),
        "uuid": str(data.get("uuid") or ""),
        "title": str(data.get("title") or ""),
        "description": str(data.get("description") or ""),
        "status": str(data.get("status") or ""),
        "source": str(data.get("source") or ""),
        "sequence": str(data.get("sequence") or ""),
        "role": _role(data.get("role") or {}),
        "license": license_value,
        "license_uuid": license_uuid,
        "created": _parse_iso_datetime(audit.get("created")),
        "updated": _parse_iso_datetime(audit.get("updated")),
        "raw": data,
    }


def _summary(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": item["name"],
        "slug": item["slug"],
        "uuid": item["uuid"],
        "title": item["title"],
        "description": item["description"],
        "status": item["status"],
        "role": item["role"],
        "updated": item["updated"],
    }


def part(part_name: str) -> dict[str, Any]:
    """Fetch an iGEM part by exact registry part ID, slug, or UUID."""

    reference = _reference(part_name)
    return _normalize(Part.get(_client(), reference))


def search(query: str, limit: int = 10) -> dict[str, Any]:
    """Search iGEM parts by free text and return summary matches."""

    query = query.strip()
    if not query:
        raise ValueError("query must not be empty")

    limit = max(1, min(int(limit), 50))
    results = [_normalize(record) for record in Part.search(_client(), query, limit=limit)]

    return {
        "query": query,
        "count": len(results),
        "results": [_summary(item) for item in results],
    }


def search_best(query: str) -> dict[str, Any]:
    """Search iGEM parts and return the best full matching part record."""

    query = query.strip()
    if not query:
        raise ValueError("query must not be empty")

    # Only try exact lookup if it looks like a UUID or valid part slug/ID.
    try:
        selected = part(query)
        return {
            "query": query,
            "selected": selected,
            "alternatives": [],
        }
    except Exception:
        # Free-text queries belong to search, not exact part lookup.
        pass

    matches = list(Part.search(_client(), query, limit=5))
    if not matches:
        raise LookupError(f"No iGEM parts matched {query!r}.")

    results = [_normalize(match) for match in matches]

    return {
        "query": query,
        "selected": results[0],
        "alternatives": [_summary(item) for item in results[1:]],
    }
