"""iGEM registry API wrapper."""

from __future__ import annotations

from igem_registry_api import Client

_IGEM_API_BASE = "https://api.registry.igem.org/v1"


def _part_name_to_slug(part_name: str) -> str:
    return part_name.lower().replace("_", "-")


def part(part_name: str) -> dict[str, str]:
    slug = _part_name_to_slug(part_name)
    client = Client(base=_IGEM_API_BASE)
    response = client.session.get(f"{client.base}/parts/slugs/{slug}", timeout=30.0)
    response.raise_for_status()
    record = response.json()
    return {
        "part": part_name,
        "title": str(record.get("title") or ""),
        "url": f"https://registry.igem.org/parts/{slug}",
        "content": response.text,
    }
