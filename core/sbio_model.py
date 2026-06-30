"""Gateway to a single SimBiology model.

Reads execute through the owning service and marshal MATLAB results into Python
types. Builders only return a MATLAB command string; the caller runs it via the
service and persists the change.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any

from engine.exceptions import ElementNotFoundError

if TYPE_CHECKING:
    from core.sbio_service import SbioService


def to_matlab_string(value: object) -> str:
    """Format a Python value as a single-quoted MATLAB string literal."""

    return "'" + str(value).replace("'", "''") + "'"


def to_matlab_number(value: float) -> str:
    """Format a Python number as a MATLAB numeric literal."""

    return repr(float(value))


def _split_reaction_spec(equation: str) -> tuple[str, str | None]:
    """Split a reaction spec into stoichiometry and optional rate."""

    parts = equation.split(";", 1)
    reaction = parts[0].strip()
    rate = parts[1].strip() if len(parts) > 1 and parts[1].strip() else None
    return reaction, rate


def _format_reaction_rate(rate: str) -> str:
    """Render a reaction rate as a MATLAB numeric literal when possible."""

    try:
        return to_matlab_number(float(rate))
    except ValueError:
        return to_matlab_string(rate)


def _finite_or_none(value: Any) -> Any:
    """Collapse non-finite floats (Inf/NaN) to None so results stay JSON-safe."""

    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _matrix(value: Any) -> list[list[float]]:
    """Normalise a MATLAB scalar/vector/matrix into a list of float rows."""

    if value is None:
        return []
    if isinstance(value, (int, float)):
        return [[float(value)]]
    rows: list[list[float]] = []
    for row in value:
        if isinstance(row, (int, float)):
            rows.append([float(row)])
        else:
            rows.append([float(item) for item in row])
    return rows


def _format_simdata(time: Any, data: Any, names: Any, units: Any) -> dict[str, Any]:
    """Marshal raw SimData arrays into a JSON-friendly time-course dict."""

    names = [names] if isinstance(names, str) else [str(name) for name in names]
    data_rows = _matrix(data)
    return {
        "time": [row[0] for row in _matrix(time)],
        "time_units": str(units),
        "names": names,
        "data": {name: [row[index] for row in data_rows] for index, name in enumerate(names)},
    }


_DETAIL: dict[str, str] = {
    "species": "struct('Name',sbio_e.Name,'Value',sbio_e.Value,'Units',sbio_e.InitialAmountUnits,'Compartment',sbio_e.Parent.Name)",
    "reaction": "struct('Name',sbio_e.Name,'Reaction',sbio_e.Reaction,'Reversible',sbio_e.Reversible)",
    "compartment": "struct('Name',sbio_e.Name,'Capacity',sbio_e.Capacity,'Units',sbio_e.CapacityUnits)",
    "parameter": "struct('Name',sbio_e.Name,'Value',sbio_e.Value,'Units',sbio_e.ValueUnits)",
}

_LIST_PROPS = {"species": "Species", "reaction": "Reactions", "compartment": "Compartments", "parameter": "Parameters"}

_FIELD_ATTRS: dict[str, dict[str, str]] = {
    "species": {"name": "Name", "value": "Value", "units": "InitialAmountUnits"},
    "reaction": {"name": "Name", "reaction": "Reaction", "reversible": "Reversible"},
    "compartment": {"name": "Name", "capacity": "Capacity", "units": "CapacityUnits"},
    "parameter": {"name": "Name", "value": "Value", "units": "ValueUnits"},
}

# Active-configset reader; ``sbio_cs`` is the selected configset. Tolerances live
# on SolverOptions and are read separately, because stochastic solvers
# (ssa/expltau/impltau) use an SSASolverOptions class that doesn't expose them.
_CONFIGSET_DETAIL = (
    "struct("
    "'StopTime',sbio_cs.StopTime,"
    "'SolverType',sbio_cs.SolverType,"
    "'TimeUnits',sbio_cs.TimeUnits,"
    "'MaximumWallClock',sbio_cs.MaximumWallClock,"
    "'MaximumNumberOfLogs',sbio_cs.MaximumNumberOfLogs)"
)

_CONFIGSET_SETTERS: dict[str, str] = {
    "stop_time": "sbio_cs.StopTime = {value};",
    "solver_type": "sbio_cs.SolverType = {value};",
    "time_units": "sbio_cs.TimeUnits = {value};",
    "absolute_tolerance": "sbio_cs.SolverOptions.AbsoluteTolerance = {value};",
    "relative_tolerance": "sbio_cs.SolverOptions.RelativeTolerance = {value};",
    "max_wall_clock": "sbio_cs.MaximumWallClock = {value};",
    "max_number_of_logs": "sbio_cs.MaximumNumberOfLogs = {value};",
}
_CONFIGSET_STRING_FIELDS = {"solver_type", "time_units"}


class SbioModel:
    """Read elements of one model and build SimBiology mutation commands."""

    def __init__(self, service: SbioService, var: str, name: str) -> None:
        self._service = service
        self.var = var  # MATLAB workspace variable holding the model
        self.name = name

    # --- reads: element name lists ---
    def species(self) -> list[str]:
        return self._names("species")

    def reactions(self) -> list[str]:
        return self._names("reaction")

    def compartments(self) -> list[str]:
        return self._names("compartment")

    def parameters(self) -> list[str]:
        return self._names("parameter")

    def _names(self, kind: str) -> list[str]:
        result = self._service.execute(f"{{{self.var}.{_LIST_PROPS[kind]}.Name}}", nargout=1)
        return [str(item) for item in (result or [])]

    # --- reads: element details ---
    def get_species(self, name: str) -> dict[str, Any]:
        return self._detail("species", name)

    def get_reaction(self, name: str) -> dict[str, Any]:
        return self._detail("reaction", name)

    def get_compartment(self, name: str) -> dict[str, Any]:
        return self._detail("compartment", name)

    def get_parameter(self, name: str) -> dict[str, Any]:
        return self._detail("parameter", name)

    def _detail(self, kind: str, name: str) -> dict[str, Any]:
        self._service.execute(f"sbio_e = {self._select(kind, name)};")
        if self._service.execute("isempty(sbio_e)", nargout=1):
            raise ElementNotFoundError(f"No {kind} named {name!r} in model {self.name!r}.")
        return self._service.execute(_DETAIL[kind], nargout=1)

    # --- builders: return a MATLAB command string (do not execute) ---
    def add_species_cmd(self, compartment: str, name: str, amount: float) -> str:
        return f"addspecies({self._select('compartment', compartment)},{to_matlab_string(name)},{to_matlab_number(amount)});"

    def add_reaction_cmd(self, name: str, equation: str) -> str:
        reaction, rate = _split_reaction_spec(equation)
        command = f"rxnObj = addreaction({self.var},{to_matlab_string(reaction)}); set(rxnObj,'Name',{to_matlab_string(name)});"
        return command if rate is None else f"{command} rxnObj.ReactionRate = {_format_reaction_rate(rate)};"

    def add_compartment_cmd(self, name: str) -> str:
        return f"addcompartment({self.var},{to_matlab_string(name)});"

    def add_parameter_cmd(self, name: str, value: float) -> str:
        return f"addparameter({self.var},{to_matlab_string(name)},{to_matlab_number(value)});"

    def rename_model_cmd(self, new_name: str) -> str:
        return f"{self.var}.Name = {to_matlab_string(new_name)};"

    def delete_model_cmd(self) -> str:
        return f"delete({self.var});"

    def delete_species_cmd(self, name: str) -> str:
        return self._delete_cmd("species", name)

    def delete_reaction_cmd(self, name: str) -> str:
        return self._delete_cmd("reaction", name)

    def delete_compartment_cmd(self, name: str) -> str:
        return self._delete_cmd("compartment", name)

    def delete_parameter_cmd(self, name: str) -> str:
        return self._delete_cmd("parameter", name)

    def set_species_cmd(self, name: str, **fields: Any) -> str:
        return self._set_cmd("species", name, fields)

    def set_reaction_cmd(self, name: str, **fields: Any) -> str:
        return self._set_cmd("reaction", name, fields)

    def set_compartment_cmd(self, name: str, **fields: Any) -> str:
        return self._set_cmd("compartment", name, fields)

    def set_parameter_cmd(self, name: str, **fields: Any) -> str:
        return self._set_cmd("parameter", name, fields)

    def _select(self, kind: str, name: str) -> str:
        return f"sbioselect({self.var},'Type',{to_matlab_string(kind)},'Name',{to_matlab_string(name)})"

    def _delete_cmd(self, kind: str, name: str) -> str:
        return f"delete({self._select(kind, name)});"

    def _set_cmd(self, kind: str, name: str, fields: dict[str, Any]) -> str:
        updates = [f"sbio_e = {self._select(kind, name)};"]
        for field, value in fields.items():
            key = field.lower()
            if key not in _FIELD_ATTRS[kind]:
                raise KeyError(f"Unsupported {kind} field: {field}")
            attr = _FIELD_ATTRS[kind][key]
            if key == "reversible":
                value = "true" if bool(value) else "false"
            elif key in {"name", "reaction", "units"} or attr.endswith("Name") or attr.endswith("Units"):
                value = to_matlab_string(value)
            else:
                value = to_matlab_number(value)
            updates.append(f"sbio_e.{attr} = {value};")
        return " ".join(updates)

    # --- simulation: configset read + builder, and the run itself ---
    def get_configset(self) -> dict[str, Any]:
        """Return the active configset's settings (tolerances only when exposed)."""

        self._service.execute(f"sbio_cs = getconfigset({self.var});")
        raw = self._service.execute(_CONFIGSET_DETAIL, nargout=1)
        settings = {key: _finite_or_none(value) for key, value in raw.items()}
        if self._service.execute("isprop(sbio_cs.SolverOptions,'AbsoluteTolerance')", nargout=1):
            settings["AbsoluteTolerance"] = self._service.execute(
                "sbio_cs.SolverOptions.AbsoluteTolerance", nargout=1)
            settings["RelativeTolerance"] = self._service.execute(
                "sbio_cs.SolverOptions.RelativeTolerance", nargout=1)
        return settings

    def set_configset_cmd(self, **fields: Any) -> str:
        """Build commands updating the active configset (KeyError on unknown field)."""

        updates = [f"sbio_cs = getconfigset({self.var});"]
        for field, value in fields.items():
            key = field.lower()
            if key not in _CONFIGSET_SETTERS:
                raise KeyError(f"Unsupported simulation setting: {field}")
            formatted = to_matlab_string(value) if key in _CONFIGSET_STRING_FIELDS else to_matlab_number(value)
            updates.append(_CONFIGSET_SETTERS[key].format(value=formatted))
        return " ".join(updates)

    def simulate(self, species: list[str] | None = None) -> dict[str, Any]:
        """Run ``sbiosimulate`` on the active configset and return time-course data.

        If ``species`` is given, only those quantities are returned (via
        ``selectbyname``) instead of every logged state.
        """

        self._service.execute(f"sbio_sd = sbiosimulate({self.var});")
        source = "sbio_sd"
        if species:
            names_cell = "{" + ",".join(to_matlab_string(s) for s in species) + "}"
            self._service.execute(f"sbio_sd_sel = selectbyname(sbio_sd,{names_cell});")
            source = "sbio_sd_sel"
        time = self._service.execute(f"{source}.Time", nargout=1)
        data = self._service.execute(f"{source}.Data", nargout=1)
        names = self._service.execute(f"{source}.DataNames", nargout=1)
        units = self._service.execute(f"{source}.TimeUnits", nargout=1)
        return _format_simdata(time, data, names, units)
