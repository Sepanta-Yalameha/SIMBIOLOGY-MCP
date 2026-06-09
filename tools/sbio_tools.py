"""SimBiology CRUD tools exposed through MCP."""

from __future__ import annotations

from typing import Any

from core.sbio_service import SbioService
from tools.registry import register

_SERVICE = SbioService()


def _model(name: str | None = None):
    return _SERVICE.get_model(name)


@register("load_project")
def load_project(path: str) -> dict[str, Any]:
    models = _SERVICE.load_project(path)
    return {"project_path": _SERVICE.project_path, "models": models}


@register("create_project")
def create_project(model_name: str, path: str | None = None) -> dict[str, Any]:
    models = _SERVICE.create_project(model_name, path)
    return {"project_path": _SERVICE.project_path, "models": models}


@register("save_project")
def save_project(path: str | None = None) -> dict[str, Any]:
    _SERVICE.save_project(path)
    return {"project_path": path or _SERVICE.project_path}


@register("create_model")
def create_model(name: str) -> dict[str, Any]:
    model = _SERVICE.create_model(name)
    return {"name": model.name}


@register("rename_model")
def rename_model(old_name: str, new_name: str) -> dict[str, Any]:
    model = _SERVICE.rename_model(old_name, new_name)
    return {"name": model.name}


@register("remove_model")
def remove_model(name: str) -> dict[str, Any]:
    _SERVICE.delete_model(name)
    return {"removed": name}


@register("list_models")
def list_models() -> list[str]:
    return _SERVICE.model_names()


@register("list_species")
def list_species(model_name: str | None = None) -> list[str]:
    return _model(model_name).species()


@register("list_reactions")
def list_reactions(model_name: str | None = None) -> list[str]:
    return _model(model_name).reactions()


@register("list_compartments")
def list_compartments(model_name: str | None = None) -> list[str]:
    return _model(model_name).compartments()


@register("list_parameters")
def list_parameters(model_name: str | None = None) -> list[str]:
    return _model(model_name).parameters()


@register("create_compartment")
def create_compartment(name: str, model_name: str | None = None, capacity: float = 1.0) -> dict[str, Any]:
    model = _model(model_name)
    _SERVICE.execute(model.add_compartment_cmd(name))
    if capacity != 1.0:
        _SERVICE.execute(model.set_compartment_cmd(name, capacity=capacity))
    return {"name": name, "capacity": capacity}


@register("modify_compartment")
def modify_compartment(name: str, model_name: str | None = None, capacity: float | None = None, units: str | None = None) -> dict[str, Any]:
    model = _model(model_name)
    fields: dict[str, Any] = {}
    if capacity is not None:
        fields["capacity"] = capacity
    if units is not None:
        fields["units"] = units
    if fields:
        _SERVICE.execute(model.set_compartment_cmd(name, **fields))
    return {"name": name, **fields}


@register("remove_compartment")
def remove_compartment(name: str, model_name: str | None = None) -> dict[str, Any]:
    model = _model(model_name)
    _SERVICE.execute(model.delete_compartment_cmd(name))
    return {"removed": name}


@register("create_species")
def create_species(name: str, compartment: str, value: float = 0.0, model_name: str | None = None) -> dict[str, Any]:
    model = _model(model_name)
    _SERVICE.execute(model.add_species_cmd(compartment, name, value))
    return {"name": name, "compartment": compartment, "value": value}


@register("modify_species")
def modify_species(name: str, model_name: str | None = None, value: float | None = None, units: str | None = None) -> dict[str, Any]:
    model = _model(model_name)
    fields: dict[str, Any] = {}
    if value is not None:
        fields["value"] = value
    if units is not None:
        fields["units"] = units
    if fields:
        _SERVICE.execute(model.set_species_cmd(name, **fields))
    return {"name": name, **fields}


@register("remove_species")
def remove_species(name: str, model_name: str | None = None) -> dict[str, Any]:
    model = _model(model_name)
    _SERVICE.execute(model.delete_species_cmd(name))
    return {"removed": name}


@register("create_reaction")
def create_reaction(name: str, equation: str, model_name: str | None = None) -> dict[str, Any]:
    model = _model(model_name)
    _SERVICE.execute(model.add_reaction_cmd(name, equation))
    return {"name": name, "reaction": equation}


@register("modify_reaction")
def modify_reaction(name: str, model_name: str | None = None, equation: str | None = None, reversible: bool | None = None) -> dict[str, Any]:
    model = _model(model_name)
    fields: dict[str, Any] = {}
    if equation is not None:
        fields["reaction"] = equation
    if reversible is not None:
        fields["reversible"] = reversible
    if fields:
        _SERVICE.execute(model.set_reaction_cmd(name, **fields))
    return {"name": name, **fields}


@register("remove_reaction")
def remove_reaction(name: str, model_name: str | None = None) -> dict[str, Any]:
    model = _model(model_name)
    _SERVICE.execute(model.delete_reaction_cmd(name))
    return {"removed": name}


@register("create_parameter")
def create_parameter(name: str, value: float, model_name: str | None = None) -> dict[str, Any]:
    model = _model(model_name)
    _SERVICE.execute(model.add_parameter_cmd(name, value))
    return {"name": name, "value": value}


@register("modify_parameter")
def modify_parameter(name: str, model_name: str | None = None, value: float | None = None, units: str | None = None) -> dict[str, Any]:
    model = _model(model_name)
    fields: dict[str, Any] = {}
    if value is not None:
        fields["value"] = value
    if units is not None:
        fields["units"] = units
    if fields:
        _SERVICE.execute(model.set_parameter_cmd(name, **fields))
    return {"name": name, **fields}


@register("remove_parameter")
def remove_parameter(name: str, model_name: str | None = None) -> dict[str, Any]:
    model = _model(model_name)
    _SERVICE.execute(model.delete_parameter_cmd(name))
    return {"removed": name}
