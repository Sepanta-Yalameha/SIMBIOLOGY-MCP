"""iGEM registry API wrapper."""

from __future__ import annotations

from functools import lru_cache
import importlib
import pkgutil
import re
from datetime import datetime, timezone
from typing import Any, get_args
from uuid import UUID

import igem_registry_api
from igem_registry_api import Client, Part, Reference


class IgemUnavailableError(RuntimeError):
    """Raised when the iGEM registry client cannot connect."""

_PART_SLUG_RE = re.compile(r"^(?:bba-[a-z0-9]{1,10}|psb[a-z0-9]{3,5})$")


def _is_registry_model(obj: Any) -> bool:
    """Whether `obj` is one of igem_registry_api's own response models.

    The module check is the load-bearing half. Matching on shape alone also
    catches the pydantic base classes the library imports into its own
    namespace, and relaxing those reaches every model in the process rather
    than this client's: models defined afterwards would quietly accept unknown
    fields, and RootModel refuses the change outright, so any RootModel
    subclass built after the sweep raises PydanticUserError. Requiring the
    class to come from igem_registry_api keeps the change where it belongs.

    Shape is still checked first so that nothing here has to import pydantic,
    which reaches this project as a transitive dependency rather than a
    declared one.
    """
    return isinstance(obj, type) and hasattr(obj, "model_fields") and hasattr(obj, "model_rebuild") and obj.__module__.startswith(igem_registry_api.__name__)


def _nested_models(model: type) -> set[type]:
    """Model classes referenced by this model's own fields.

    Annotations are unwrapped through their type arguments first, so a model
    reached only through `list[...]`, `dict[..., ...]` or `| None` is still
    found. Checking for arguments before checking for a class matters: a
    parameterised generic can satisfy an isinstance(..., type) test on some
    Python versions, and treating one as a leaf would hide the model inside it.
    """
    found: set[type] = set()

    def walk(annotation: Any) -> None:
        arguments = get_args(annotation)
        if arguments:
            for argument in arguments:
                walk(argument)
            return
        if _is_registry_model(annotation):
            found.add(annotation)

    for field in model.model_fields.values():
        walk(field.annotation)
    return found


def _relax_response_models() -> None:
    """Let the registry client accept response fields it does not know about.

    igem_registry_api declares its response models with extra="forbid", so a
    field the server adds is a hard validation error rather than something to
    ignore. iGEM has since added fields this pinned client does not know about
    to both GET /v1/health (a `valkey` component, which made connect() raise
    ClientConnectionError while the registry itself reported status "ok") and to
    /v1/parts. Relaxing every model the library owns is therefore what the client
    needs to work at all today, not insurance against some future change:
    bypassing the health gate alone still leaves Part.get and Part.search
    failing on the parts payload.

    Nothing downstream needs the strictness: `_normalize` reads each field with
    .get() and keeps the untouched payload under "raw", so an unrecognised
    field costs nothing.

    Delete all of this once igem-registry-api ships a release that relaxes
    `extra` itself. As of 0.1.0 -- still the only release ever published -- none
    exists, which is why the shim is here rather than a version bump.

    The rebuild is not optional. Pydantic compiles a validator when the class is
    created and caches it, so mutating model_config alone changes nothing.

    Rebuild order matters and is the subtle part. Rebuilding a model captures the
    validators its nested models have *at that moment*, so rebuilding an outer
    model first bakes the inner model's strict validator back in and rebuilding
    the inner one afterwards does not propagate upwards. HealthStatus nests
    ResourceData, which is exactly where iGEM added `valkey`, so the models are
    rebuilt innermost-first rather than in whatever order they were discovered.

    Only the library's own models are touched; see `_is_registry_model` for why
    that boundary matters.
    """
    models: set[type] = set()
    for _, name, _ in pkgutil.walk_packages(igem_registry_api.__path__, f"{igem_registry_api.__name__}."):
        try:
            module = importlib.import_module(name)
        except Exception:
            # A submodule that will not import cannot supply a model the client
            # then parses a response with, so passing over it changes nothing.
            continue
        for obj in vars(module).values():
            if _is_registry_model(obj):
                models.add(obj)

    for model in models:
        model.model_config["extra"] = "allow"

    seen: set[type] = set()

    def rebuild(model: type) -> None:
        # Marking on entry does double duty: it keeps a model reached twice from
        # being rebuilt twice, and it stops a cycle between two models from
        # recursing until the stack runs out.
        if model in seen:
            return
        seen.add(model)
        for nested in _nested_models(model):
            rebuild(nested)
        try:
            model.model_rebuild(force=True)
        except Exception:
            # A model that cannot rebuild keeps whatever validator it already
            # had, which is exactly the behaviour we have today.
            pass

    # Sorted so the walk starts from the same model every run: class hashes are
    # id-based, so set iteration order changes between processes.
    for model in sorted(models, key=lambda cls: cls.__name__):
        rebuild(model)


@lru_cache(maxsize=1)
def _client() -> Client:
    _relax_response_models()
    client = Client()
    try:
        client.connect()
    except Exception as exc:
        raise IgemUnavailableError(
            "Could not connect to the iGEM registry. Check https://api.registry.igem.org/v1/health first: "
            'if it reports status "ok" then the registry is up and the fault is on this side, in the '
            "igem-registry-api client, which rejects responses whose shape the server has changed."
        ) from exc
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
