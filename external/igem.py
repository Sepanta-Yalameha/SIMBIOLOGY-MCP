"""iGEM registry API wrapper."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from igem_registry_api import Client

_IGEM_API_BASE = "https://api.registry.igem.org/v1"


def _part_name_to_slug(part_name: str) -> str:
    return part_name.lower().replace("_", "-")


def _safe_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _parse_iso_datetime(value: str | None) -> str | None:
    if not value:
        return None
    try:
        # Preserve a normalized ISO-8601 timestamp if the registry returns one.
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc).isoformat()
    except ValueError:
        return value


def _sequence_stats(sequence: str | None) -> dict[str, Any]:
    if not sequence:
        return {}
    seq = sequence.upper()
    length = len(seq)
    gc = sum(1 for base in seq if base in {"G", "C"})
    at = sum(1 for base in seq if base in {"A", "T"})
    stats: dict[str, Any] = {
        "sequence_length": length,
        "gc_count": gc,
        "at_count": at,
        "gc_fraction": round(gc / length, 4) if length else None,
    }
    return stats


def part(part_name: str) -> dict[str, Any]:
    slug = _part_name_to_slug(part_name)
    client = Client(base=_IGEM_API_BASE)
    response = client.session.get(f"{client.base}/parts/slugs/{slug}", timeout=30.0)
    response.raise_for_status()
    record = response.json()
    sequence = record.get("sequence")
    audit = record.get("audit") or {}
    role = record.get("role") or {}
    chassis = record.get("chassis") or {}
    designed_for = chassis.get("designedFor") or []
    characterised_in = chassis.get("characterisedIn") or []
    content = json.dumps(record, ensure_ascii=True, sort_keys=True)
    return {
        "part": part_name,
        "title": str(record.get("title") or ""),
        "description": str(record.get("description") or ""),
        "status": str(record.get("status") or ""),
        "source": str(record.get("source") or ""),
        "slug": str(record.get("slug") or slug),
        "url": f"https://registry.igem.org/parts/{slug}",
        "sequence": str(sequence or ""),
        "sequence_length": _safe_int(len(sequence)) if sequence else None,
        "sequence_preview": str(sequence[:60]) + ("..." if sequence and len(sequence) > 60 else "") if sequence else "",
        "sequence_stats": _sequence_stats(sequence),
        "created": _parse_iso_datetime(audit.get("created")),
        "updated": _parse_iso_datetime(audit.get("updated")),
        "role": {
            "uuid": str(role.get("uuid") or ""),
            "accession": str(role.get("accession") or ""),
            "label": str(role.get("label") or ""),
            "deprecated": bool(role.get("deprecated")) if role else False,
        },
        "license_uuid": str(record.get("licenseUUID") or ""),
        "chassis": {
            "designed_for_count": len(designed_for),
            "characterised_in_count": len(characterised_in),
        },
        "content": content,
    }
