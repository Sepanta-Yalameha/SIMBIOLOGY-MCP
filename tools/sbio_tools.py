"""SimBiology CRUD tools exposed through MCP.

Each tool is an explicit, typed, documented function so FastMCP generates a
precise schema and description per tool. The shared plumbing (resolving the
model, running a command, echoing the result) lives in the helpers below.
"""

from __future__ import annotations

from collections.abc import Callable
from io import StringIO
import csv
from pathlib import Path
from typing import Any, Literal

from core.sbio_model import SbioModel, build_reaction_equation, to_matlab_string
from core.sbio_service import SbioService
from tools.registry import register

SolverType = Literal["ode15s", "ode23t", "ode45", "sundials", "ssa", "expltau", "impltau"]

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


def _add(model_name: str | None, build: Callable[[SbioModel], str], **echo: Any) -> dict[str, Any]:
    """Run an element-creation command and echo back the created fields."""

    _run(build(_model(model_name)))
    return echo


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
    _add(model_name, lambda m: m.add_compartment_cmd(name), name=name, capacity=capacity)
    if capacity != 1.0:
        _run(_model(model_name).set_compartment_cmd(name, capacity=capacity))
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
    return _add(model_name, lambda m: m.add_species_cmd(compartment, name, value), name=name, compartment=compartment, value=value)


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
def create_reaction(
    name: str,
    model_name: str | None = None,
    left: str = "",
    right: str = "",
    reversible: bool = False,
    rate: str | None = None,
) -> dict[str, Any]:
    """Create a reaction in a model.

    Use plain left/right reaction strings. Use ``null`` explicitly for sources
    or sinks. Keep ``rate`` as a raw kinetic expression string.
    """

    equation = build_reaction_equation(left, right, reversible=reversible)
    if rate is not None:
        equation = f"{equation}; {rate}"
    return _add(model_name, lambda m: m.add_reaction_cmd(name, equation), name=name, left=left, right=right, reversible=reversible, rate=rate)


@register("modify_reaction")
def modify_reaction(
    name: str,
    model_name: str | None = None,
    left: str = "",
    right: str = "",
    reversible: bool | None = None,
    rate: str | None = None,
) -> dict[str, Any]:
    """Modify a reaction in a model.

    Pass ``left``/``right`` only when changing the stoichiometry; omit them to
    change just ``reversible`` or ``rate``. The rate stays a raw kinetic
    expression string.
    """

    data: dict[str, Any] = {}
    if left or right:
        data["reaction"] = build_reaction_equation(left, right, reversible=bool(reversible))
    if reversible is not None:
        data["reversible"] = reversible
    if rate is not None:
        data["rate"] = rate
    return _modify(model_name, "reaction", name, **data)


@register("remove_reaction")
def remove_reaction(name: str, model_name: str | None = None) -> dict[str, Any]:
    """Remove a reaction from a model."""
    return _remove(model_name, "reaction", name)


# parameters
@register("create_parameter")
def create_parameter(name: str, value: float, model_name: str | None = None) -> dict[str, Any]:
    """Create a parameter in a model."""
    return _add(model_name, lambda m: m.add_parameter_cmd(name, value), name=name, value=value)


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


# doses
@register("create_dose")
def create_dose(
    name: str,
    target: str,
    model_name: str | None = None,
    dose_type: str = "repeat",
    amount: float | None = None,
    start_time: float | None = None,
    interval: float | None = None,
    repeat_count: int | None = None,
    rate: float | None = None,
    amount_units: str | None = None,
    rate_units: str | None = None,
    time_units: str | None = None,
    times: list[float] | None = None,
    amounts: list[float] | None = None,
    rates: list[float] | None = None,
) -> dict[str, Any]:
    """Create a dose targeting a species in a model.

    ``dose_type='repeat'`` uses the scalar fields ``amount``, ``start_time``,
    ``interval``, ``repeat_count`` (additional doses after the first), and
    ``rate`` (0 = bolus, >0 = zero-order infusion). ``dose_type='schedule'``
    uses the paired lists ``times``, ``amounts``, and ``rates``. Note: a model
    with doses must simulate with an ODE solver (not ssa/expltau/impltau).
    """

    return _add(
        model_name,
        lambda m: m.add_dose_cmd(
            name,
            target,
            dose_type=dose_type,
            amount=amount,
            start_time=start_time,
            interval=interval,
            repeat_count=repeat_count,
            rate=rate,
            amount_units=amount_units,
            rate_units=rate_units,
            time_units=time_units,
            times=times,
            amounts=amounts,
            rates=rates,
        ),
        name=name,
        target=target,
        dose_type=dose_type,
        amount=amount,
        start_time=start_time,
        interval=interval,
        repeat_count=repeat_count,
        rate=rate,
        amount_units=amount_units,
        rate_units=rate_units,
        time_units=time_units,
        times=times,
        amounts=amounts,
        rates=rates,
    )


@register("modify_dose")
def modify_dose(
    name: str,
    model_name: str | None = None,
    target: str | None = None,
    amount: float | None = None,
    rate: float | None = None,
    interval: float | None = None,
    start_time: float | None = None,
    repeat_count: int | None = None,
    amount_units: str | None = None,
    rate_units: str | None = None,
    time_units: str | None = None,
) -> dict[str, Any]:
    """Modify a repeat dose's scalar fields.

    Only repeat-dose scalar fields are supported. To change a schedule dose (its
    ``Time``/``Amount``/``Rate`` vectors), remove it and recreate it with
    ``create_dose``.
    """
    return _modify(
        model_name,
        "dose",
        name,
        target=target,
        amount=amount,
        rate=rate,
        interval=interval,
        start_time=start_time,
        repeat_count=repeat_count,
        amount_units=amount_units,
        rate_units=rate_units,
        time_units=time_units,
    )


@register("list_doses")
def list_doses(model_name: str | None = None) -> list[str]:
    """List doses in a SimBiology model."""
    return _model(model_name).doses()


@register("remove_dose")
def remove_dose(name: str, model_name: str | None = None) -> dict[str, Any]:
    """Remove a dose from a model."""
    return _remove(model_name, "dose", name)


# variants
@register("create_variant")
def create_variant(
    name: str,
    content: list[dict[str, Any]],
    model_name: str | None = None,
) -> dict[str, Any]:
    """Create a variant in a model.

    ``content`` is a list of dicts, each ``{"type","name","property","value"}``.
    Type->property: parameter->'Value', species->'InitialAmount',
    compartment->'Capacity'. A knockout is an entry with ``value`` 0.
    """
    return _add(model_name, lambda m: m.add_variant_cmd(name, content), name=name, content=content)


@register("modify_variant")
def modify_variant(
    name: str,
    content: list[dict[str, Any]],
    model_name: str | None = None,
) -> dict[str, Any]:
    """Modify a variant, replacing its entire content.

    ``content`` (list of ``{"type","name","property","value"}`` dicts) replaces
    all existing entries. Must be non-empty (use ``remove_variant`` to delete a
    variant); an empty list would silently wipe all content.
    """
    if not content:
        raise ValueError("modify_variant replaces all content; provide at least one entry.")
    return _modify(model_name, "variant", name, content=content)


@register("list_variants")
def list_variants(model_name: str | None = None) -> list[str]:
    """List variants in a SimBiology model."""
    return _model(model_name).variants()


@register("remove_variant")
def remove_variant(name: str, model_name: str | None = None) -> dict[str, Any]:
    """Remove a variant from a model."""
    return _remove(model_name, "variant", name)


@register("simulate_model")
def simulate_model(
    model_name: str | None = None,
    species: list[str] | None = None,
    doses: list[str] | None = None,
    variants: list[str] | None = None,
) -> dict[str, Any]:
    """Run a SimBiology model simulation and return time-course results.

    If ``species`` is given, only those quantities are returned instead of every
    logged state. Named ``doses`` and/or ``variants`` are applied by name for
    this run (via the 4-arg sbiosimulate), regardless of their Active flag.
    """
    return _model(model_name).simulate(species=species, doses=doses, variants=variants)


@register("export_graph")
def export_graph(
    model_name: str | None = None,
    path: str | None = None,
    resolution: int = 300,
) -> dict[str, Any]:
    """Export the SimBiology plot as a PNG image."""

    model = _model(model_name)
    target = Path(path or "simbiology_plot.png")
    _svc().execute(f"sim_data = sbiosimulate({model.var});")
    _svc().execute("axes_handle = sbioplot(sim_data);")
    _svc().execute("fig_handle = get(axes_handle, 'Parent');")
    _svc().execute(f"exportgraphics(fig_handle, {to_matlab_string(str(target))}, 'Resolution', {int(resolution)});")
    return {"path": str(target), "resolution": int(resolution)}


@register("export_csv")
def export_csv(model_name: str | None = None) -> dict[str, Any]:
    """Export the model inventory as CSV text."""

    model = _model(model_name)
    rows = [
        ("kind", "name"),
        *[("species", name) for name in model.species()],
        *[("reaction", name) for name in model.reactions()],
        *[("compartment", name) for name in model.compartments()],
        *[("parameter", name) for name in model.parameters()],
    ]
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerows(rows)
    return {"csv": buffer.getvalue()}
