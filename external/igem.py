"""iGEM registry API wrapper."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from igem_registry_api import Client

_IGEM_API_BASE = "https://api.registry.igem.org/v1"
_PREVIEW_WIDTH = 60


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


def _sequence_stats(sequence: str) -> dict[str, Any]:
    """Base composition for a DNA/RNA sequence (empty dict when absent)."""

    if not sequence:
        return {}
    seq = sequence.upper()
    gc = sum(base in "GC" for base in seq)
    at = sum(base in "AT" for base in seq)
    return {"gc_count": gc, "at_count": at, "gc_fraction": round(gc / len(seq), 4)}


def _preview(sequence: str) -> str:
    if len(sequence) <= _PREVIEW_WIDTH:
        return sequence
    return sequence[:_PREVIEW_WIDTH] + "..."


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
    sequence = str(record.get("sequence") or "")
    audit = record.get("audit") or {}
    chassis = record.get("chassis") or {}
    return {
        "part": part_name,
        "slug": str(record.get("slug") or slug),
        "url": f"https://registry.igem.org/parts/{slug}",
        "title": str(record.get("title") or ""),
        "description": str(record.get("description") or ""),
        "status": str(record.get("status") or ""),
        "source": str(record.get("source") or ""),
        "sequence": sequence,
        "sequence_length": len(sequence),
        "sequence_preview": _preview(sequence),
        "sequence_stats": _sequence_stats(sequence),
        "created": _parse_iso_datetime(audit.get("created")),
        "updated": _parse_iso_datetime(audit.get("updated")),
        "role": _role(record.get("role") or {}),
        "license_uuid": str(record.get("licenseUUID") or ""),
        "chassis": {
            "designed_for_count": len(chassis.get("designedFor") or []),
            "characterised_in_count": len(chassis.get("characterisedIn") or []),
        },
        "content": json.dumps(record, ensure_ascii=True, sort_keys=True),
    }
