"""iGEM registry API wrapper."""

from __future__ import annotations

from urllib.parse import urlencode

import httpx

_IGEM_PARTS_BASE = "https://parts.igem.org/partsdb/get_part.cgi"


def _get(url: str, params: dict[str, str] | None = None) -> httpx.Response:
    response = httpx.get(url, params=params, timeout=20.0, follow_redirects=True)
    response.raise_for_status()
    return response


def part(part_name: str) -> dict[str, str]:
    response = _get(_IGEM_PARTS_BASE, {"part": part_name})
    text = response.text
    title = ""
    for line in text.splitlines():
        if line.strip().startswith("Part "):
            title = line.strip()
            break
    return {
        "part": part_name,
        "title": title,
        "url": f"{_IGEM_PARTS_BASE}?{urlencode({'part': part_name})}",
        "content": text,
    }
