"""iGEM registry API wrapper."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from igem_registry_api import Client

_IGEM_API_BASE = "https://api.registry.igem.org/v1"
def _part_name_to_slug(part_name: str) -> str:
    return part_name.lower().replace("_", "-")


def _parse_iso_datetime(value: str | None) -> str | None:
    """Normalize a registry timestamp to UTC ISO-8601, or pass it through."""

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


def _fetch_part(slug: str) -> dict[str, Any]:
    client = Client(base=_IGEM_API_BASE)
    response = client.session.get(f"{client.base}/parts/slugs/{slug}", timeout=30.0)
    response.raise_for_status()
    return response.json()


def part(part_name: str) -> dict[str, Any]:
    """Fetch an iGEM part and return a normalized record."""

    slug = _part_name_to_slug(part_name)
    record = _fetch_part(slug)
    return {
        "part": part_name,
        "slug": str(record.get("slug") or slug),
        "title": str(record.get("title") or ""),
        "description": str(record.get("description") or ""),
        "status": str(record.get("status") or ""),
        "source": str(record.get("source") or ""),
        "sequence": str(record.get("sequence") or ""),
        "created": _parse_iso_datetime((record.get("audit") or {}).get("created")),
        "updated": _parse_iso_datetime((record.get("audit") or {}).get("updated")),
        "role": _role(record.get("role") or {}),
        "license_uuid": str(record.get("licenseUUID") or ""),
    }
