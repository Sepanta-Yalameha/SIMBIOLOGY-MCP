"""SimBiology CRUD tools exposed through MCP.

Each tool is an explicit, typed, documented function so FastMCP generates a
precise schema and description per tool. The shared plumbing (resolving the
model, running a command, echoing the result) lives in the helpers below.
"""

from __future__ import annotations

from typing import Any, Literal

from core.sbio_model import SbioModel
from core.sbio_service import SbioService
from tools.registry import register

SolverType = Literal[
    "ode15s", "ode23t", "ode45", "sundials", "ssa", "expltau", "impltau"
]

_service: SbioService | None = None


def _svc() -> SbioService:
    """Return the shared SimBiology session, starting MATLAB on first use."""

    global _service
    if _service is None:
        _service = SbioService()
    return _service


def _model(name: str | None = None) -> SbioModel:
    return _svc().get_model(name)


def _run(command: str) -> None:
    _svc().execute(command)


def _modify(model_name: str | None, kind: str, name: str, **fields: Any) -> dict[str, Any]:
    """Apply the non-None updates to an element via its ``set_<kind>_cmd`` builder."""

    data = {key: value for key, value in fields.items() if value is not None}
    if data:
        _run(getattr(_model(model_name), f"set_{kind}_cmd")(name, **data))
    return {"name": name, **data}


def _remove(model_name: str | None, kind: str, name: str) -> dict[str, Any]:
    """Delete an element via its ``delete_<kind>_cmd`` builder."""

    _run(getattr(_model(model_name), f"delete_{kind}_cmd")(name))
    return {"removed": name}

# projects
@register("load_project")
def load_project(path: str) -> dict[str, Any]:
    """Load a SimBiology project."""
    models = _svc().load_project(path)
    return {"project_path": _svc().project_path, "models": models}


@register("create_project")
def create_project(model_name: str, path: str | None = None) -> dict[str, Any]:
    """Create a new SimBiology project."""
    models = _svc().create_project(model_name, path)
    return {"project_path": _svc().project_path, "models": models}


@register("save_project")
def save_project(path: str | None = None) -> dict[str, Any]:
    """Save the current SimBiology project."""
    _svc().save_project(path)
    return {"project_path": path or _svc().project_path}

# models
@register("create_model")
def create_model(name: str) -> dict[str, Any]:
    """Create a SimBiology model."""
    return {"name": _svc().create_model(name).name}


@register("rename_model")
def rename_model(old_name: str, new_name: str) -> dict[str, Any]:
    """Rename a SimBiology model."""
    return {"name": _svc().rename_model(old_name, new_name).name}


@register("remove_model")
def remove_model(name: str) -> dict[str, Any]:
    """Remove a SimBiology model."""
    _svc().delete_model(name)
    return {"removed": name}


@register("list_models")
def list_models() -> list[str]:
    """List loaded SimBiology models."""
    return _svc().model_names()

# reads
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

# compartments
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
    return _modify(model_name, "compartment", name, capacity=capacity, units=units)


@register("remove_compartment")
def remove_compartment(name: str, model_name: str | None = None) -> dict[str, Any]:
    """Remove a compartment from a model."""
    return _remove(model_name, "compartment", name)

# species
@register("create_species")
def create_species(name: str, compartment: str, value: float = 0.0, model_name: str | None = None) -> dict[str, Any]:
    """Create a species in a model."""
    _run(_model(model_name).add_species_cmd(compartment, name, value))
    return {"name": name, "compartment": compartment, "value": value}

@register("modify_species")
def modify_species(name: str, model_name: str | None = None, value: float | None = None, units: str | None = None) -> dict[str, Any]:
    """Modify a species in a model."""
    return _modify(model_name, "species", name, value=value, units=units)


@register("remove_species")
def remove_species(name: str, model_name: str | None = None) -> dict[str, Any]:
    """Remove a species from a model."""
    return _remove(model_name, "species", name)

# reactions
@register("create_reaction")
def create_reaction(name: str, equation: str, model_name: str | None = None) -> dict[str, Any]:
    """Create a reaction in a model."""
    _run(_model(model_name).add_reaction_cmd(name, equation))
    return {"name": name, "reaction": equation}

@register("modify_reaction")
def modify_reaction(name: str, model_name: str | None = None, equation: str | None = None, reversible: bool | None = None) -> dict[str, Any]:
    """Modify a reaction in a model."""
    return _modify(model_name, "reaction", name, reaction=equation, reversible=reversible)


@register("remove_reaction")
def remove_reaction(name: str, model_name: str | None = None) -> dict[str, Any]:
    """Remove a reaction from a model."""
    return _remove(model_name, "reaction", name)

# parameters
@register("create_parameter")
def create_parameter(name: str, value: float, model_name: str | None = None) -> dict[str, Any]:
    """Create a parameter in a model."""
    _run(_model(model_name).add_parameter_cmd(name, value))
    return {"name": name, "value": value}

@register("modify_parameter")
def modify_parameter(name: str, model_name: str | None = None, value: float | None = None, units: str | None = None) -> dict[str, Any]:
    """Modify a parameter in a model."""
    return _modify(model_name, "parameter", name, value=value, units=units)


@register("remove_parameter")
def remove_parameter(name: str, model_name: str | None = None) -> dict[str, Any]:
    """Remove a parameter from a model."""
    return _remove(model_name, "parameter", name)

# simulation
@register("get_simulation_settings")
def get_simulation_settings(model_name: str | None = None) -> dict[str, Any]:
    """Get the current simulation settings (configset) for a model."""
    return _model(model_name).get_configset()


@register("configure_simulation")
def configure_simulation(
    model_name: str | None = None,
    stop_time: float | None = None,
    solver_type: SolverType | None = None,
    time_units: str | None = None,
    absolute_tolerance: float | None = None,
    relative_tolerance: float | None = None,
    max_wall_clock: float | None = None,
    max_number_of_logs: float | None = None,
) -> dict[str, Any]:
    """Configure simulation settings (stop time, solver, tolerances) for a model."""
    model = _model(model_name)
    fields = {
        key: value
        for key, value in {
            "stop_time": stop_time,
            "solver_type": solver_type,
            "time_units": time_units,
            "absolute_tolerance": absolute_tolerance,
            "relative_tolerance": relative_tolerance,
            "max_wall_clock": max_wall_clock,
            "max_number_of_logs": max_number_of_logs,
        }.items()
        if value is not None
    }
    if fields:
        _run(model.set_configset_cmd(**fields))
    return model.get_configset()


@register("simulate_model")
def simulate_model(
    model_name: str | None = None,
    species: list[str] | None = None,
) -> dict[str, Any]:
    """Run a SimBiology model simulation and return time-course results.

    If ``species`` is given, only those quantities are returned instead of every
    logged state.
    """
    return _model(model_name).simulate(species=species)
