"""SimBiology CRUD tools exposed through MCP."""

from __future__ import annotations

from typing import Any

from core.sbio_service import SbioService
from tools.registry import register

_SERVICE = SbioService()


def _model(name: str | None = None):
    return _SERVICE.get_model(name)


def _run(command: str) -> None:
    _SERVICE.execute(command)


def _modify(model_name: str | None, name: str, builder, **fields: Any) -> dict[str, Any]:
    model = _model(model_name)
    data = {key: value for key, value in fields.items() if value is not None}
    if data:
        _run(builder(model, name, **data))
    return {"name": name, **data}


@register("load_project")
def load_project(path: str) -> dict[str, Any]:
    """Load a SimBiology project."""
    models = _SERVICE.load_project(path)
    return {"project_path": _SERVICE.project_path, "models": models}


@register("create_project")
def create_project(model_name: str, path: str | None = None) -> dict[str, Any]:
    """Create a new SimBiology project."""
    models = _SERVICE.create_project(model_name, path)
    return {"project_path": _SERVICE.project_path, "models": models}


@register("save_project")
def save_project(path: str | None = None) -> dict[str, Any]:
    """Save the current SimBiology project."""
    _SERVICE.save_project(path)
    return {"project_path": path or _SERVICE.project_path}


@register("create_model")
def create_model(name: str) -> dict[str, Any]:
    """Create a SimBiology model."""
    model = _SERVICE.create_model(name)
    return {"name": model.name}


@register("rename_model")
def rename_model(old_name: str, new_name: str) -> dict[str, Any]:
    """Rename a SimBiology model."""
    model = _SERVICE.rename_model(old_name, new_name)
    return {"name": model.name}


@register("remove_model")
def remove_model(name: str) -> dict[str, Any]:
    """Remove a SimBiology model."""
    _SERVICE.delete_model(name)
    return {"removed": name}


@register("list_models")
def list_models() -> list[str]:
    """List loaded SimBiology models."""
    return _SERVICE.model_names()


@register("list_species")
def list_species(model_name: str | None = None) -> list[str]:
    """List species in a SimBiology model."""
    return _model(model_name).species()


@register("list_reactions")
def list_reactions(model_name: str | None = None) -> list[str]:
    """List reactions in a SimBiology model."""
    return _model(model_name).reactions()


@register("list_compartments")
def list_compartments(model_name: str | None = None) -> list[str]:
    """List compartments in a SimBiology model."""
    return _model(model_name).compartments()


@register("list_parameters")
def list_parameters(model_name: str | None = None) -> list[str]:
    """List parameters in a SimBiology model."""
    return _model(model_name).parameters()


@register("create_compartment")
def create_compartment(name: str, model_name: str | None = None, capacity: float = 1.0) -> dict[str, Any]:
    """Create a compartment in a model."""
    model = _model(model_name)
    _run(model.add_compartment_cmd(name))
    if capacity != 1.0:
        _run(model.set_compartment_cmd(name, capacity=capacity))
    return {"name": name, "capacity": capacity}


@register("modify_compartment")
def modify_compartment(name: str, model_name: str | None = None, capacity: float | None = None, units: str | None = None) -> dict[str, Any]:
    """Modify a compartment in a model."""
    return _modify(
        model_name,
        name,
        lambda model, name, **fields: model.set_compartment_cmd(name, **fields),
        capacity=capacity,
        units=units,
    )


@register("remove_compartment")
def remove_compartment(name: str, model_name: str | None = None) -> dict[str, Any]:
    """Remove a compartment from a model."""
    model = _model(model_name)
    _run(model.delete_compartment_cmd(name))
    return {"removed": name}


@register("create_species")
def create_species(name: str, compartment: str, value: float = 0.0, model_name: str | None = None) -> dict[str, Any]:
    """Create a species in a model."""
    model = _model(model_name)
    _run(model.add_species_cmd(compartment, name, value))
    return {"name": name, "compartment": compartment, "value": value}


@register("modify_species")
def modify_species(name: str, model_name: str | None = None, value: float | None = None, units: str | None = None) -> dict[str, Any]:
    """Modify a species in a model."""
    return _modify(
        model_name,
        name,
        lambda model, name, **fields: model.set_species_cmd(name, **fields),
        value=value,
        units=units,
    )


@register("remove_species")
def remove_species(name: str, model_name: str | None = None) -> dict[str, Any]:
    """Remove a species from a model."""
    model = _model(model_name)
    _run(model.delete_species_cmd(name))
    return {"removed": name}


@register("create_reaction")
def create_reaction(name: str, equation: str, model_name: str | None = None) -> dict[str, Any]:
    """Create a reaction in a model."""
    model = _model(model_name)
    _run(model.add_reaction_cmd(name, equation))
    return {"name": name, "reaction": equation}


@register("modify_reaction")
def modify_reaction(name: str, model_name: str | None = None, equation: str | None = None, reversible: bool | None = None) -> dict[str, Any]:
    """Modify a reaction in a model."""
    return _modify(
        model_name,
        name,
        lambda model, name, **fields: model.set_reaction_cmd(name, **fields),
        reaction=equation,
        reversible=reversible,
    )


@register("remove_reaction")
def remove_reaction(name: str, model_name: str | None = None) -> dict[str, Any]:
    """Remove a reaction from a model."""
    model = _model(model_name)
    _run(model.delete_reaction_cmd(name))
    return {"removed": name}


@register("create_parameter")
def create_parameter(name: str, value: float, model_name: str | None = None) -> dict[str, Any]:
    """Create a parameter in a model."""
    model = _model(model_name)
    _run(model.add_parameter_cmd(name, value))
    return {"name": name, "value": value}


@register("modify_parameter")
def modify_parameter(name: str, model_name: str | None = None, value: float | None = None, units: str | None = None) -> dict[str, Any]:
    """Modify a parameter in a model."""
    return _modify(
        model_name,
        name,
        lambda model, name, **fields: model.set_parameter_cmd(name, **fields),
        value=value,
        units=units,
    )


@register("remove_parameter")
def remove_parameter(name: str, model_name: str | None = None) -> dict[str, Any]:
    """Remove a parameter from a model."""
    model = _model(model_name)
    _run(model.delete_parameter_cmd(name))
    return {"removed": name}
