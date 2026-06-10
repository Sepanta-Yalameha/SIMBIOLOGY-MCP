"""iGEM registry API wrapper."""

from __future__ import annotations

import requests

from igem_registry_api import Client
from igem_registry_api.client import Mode

_IGEM_API_BASE = "https://api.registry.igem.org/v1"


def _part_name_to_slug(part_name: str) -> str:
    return part_name.lower().replace("_", "-")


def part(part_name: str) -> dict[str, str]:
    slug = _part_name_to_slug(part_name)
    client = Client.stub()
    client.base = _IGEM_API_BASE
    client.mode = Mode.ANON
    client.session = requests.Session()
    response = client.session.get(f"{client.base}/parts/slugs/{slug}", timeout=30.0)
    response.raise_for_status()
    record = response.json()
    return {
        "part": part_name,
        "title": str(record.get("title") or ""),
        "url": f"https://registry.igem.org/parts/{slug}",
        "content": response.text,
    }
