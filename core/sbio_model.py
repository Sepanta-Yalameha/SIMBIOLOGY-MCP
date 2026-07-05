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


def build_reaction_equation(
    left: str,
    right: str,
    reversible: bool = False,
) -> str:
    """Build a SimBiology reaction equation from left/right strings."""

    arrow = "<->" if reversible else "->"
    return f"{left.strip()} {arrow} {right.strip()}"


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


def _matlab_column(values: Any) -> str:
    """Format a sequence of numbers as a MATLAB numeric column-vector literal."""

    return "[" + ";".join(to_matlab_number(value) for value in values) + "]"


def _matlab_string_cell(values: list[str]) -> str:
    """Format a list of strings as a MATLAB cell array of strings."""

    return "{" + ",".join(to_matlab_string(value) for value in values) + "}"


def _matlab_variant_value(value: Any) -> str:
    """Format a variant content value (numeric via number, otherwise string).

    ``bool`` is a subclass of ``int``, so ``True``/``False`` render as ``1.0``/
    ``0.0`` rather than a quoted string SimBiology would reject for a numeric
    property.
    """

    if isinstance(value, (int, float)):
        return to_matlab_number(value)
    return to_matlab_string(value)


def _matlab_content(content: list[dict[str, Any]]) -> str:
    """Render variant content dicts as a MATLAB cell array of 4-tuples."""

    entries = []
    for entry in content:
        missing = [key for key in ("type", "name", "property", "value") if key not in entry]
        if missing:
            raise ValueError(f"Variant content entry is missing keys {missing}: {entry!r}")
        entries.append(
            "{"
            + ",".join(
                (
                    to_matlab_string(entry["type"]),
                    to_matlab_string(entry["name"]),
                    to_matlab_string(entry["property"]),
                    _matlab_variant_value(entry["value"]),
                )
            )
            + "}"
        )
    return "{" + ",".join(entries) + "}"


_DETAIL: dict[str, str] = {
    "species": "struct('Name',sbio_e.Name,'Value',sbio_e.Value,'Units',sbio_e.InitialAmountUnits,'Compartment',sbio_e.Parent.Name)",
    "reaction": "struct('Name',sbio_e.Name,'Reaction',sbio_e.Reaction,'Reversible',sbio_e.Reversible)",
    "compartment": "struct('Name',sbio_e.Name,'Capacity',sbio_e.Capacity,'Units',sbio_e.CapacityUnits)",
    "parameter": "struct('Name',sbio_e.Name,'Value',sbio_e.Value,'Units',sbio_e.ValueUnits)",
}

_LIST_PROPS = {
    "species": "Species",
    "reaction": "Reactions",
    "compartment": "Compartments",
    "parameter": "Parameters",
    "dose": "Doses",
    "variant": "Variants",
}

_FIELD_ATTRS: dict[str, dict[str, str]] = {
    "species": {"name": "Name", "value": "Value", "units": "InitialAmountUnits"},
    "reaction": {"name": "Name", "reaction": "Reaction", "reversible": "Reversible", "rate": "ReactionRate"},
    "compartment": {"name": "Name", "capacity": "Capacity", "units": "CapacityUnits"},
    "parameter": {"name": "Name", "value": "Value", "units": "ValueUnits"},
}

# Dose field -> object attribute; doses use getdose/getvariant, not sbioselect Types.
_DOSE_FIELDS: dict[str, str] = {
    "target": "TargetName",
    "amount": "Amount",
    "rate": "Rate",
    "interval": "Interval",
    "start_time": "StartTime",
    "repeat_count": "RepeatCount",
    "amount_units": "AmountUnits",
    "rate_units": "RateUnits",
    "time_units": "TimeUnits",
}
_DOSE_STRING_FIELDS = {"target", "amount_units", "rate_units", "time_units"}

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

    def doses(self) -> list[str]:
        return self._names("dose")

    def variants(self) -> list[str]:
        return self._names("variant")

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

    def get_dose(self, name: str) -> dict[str, Any]:
        """Return a dose's settings, reading only the type-appropriate fields."""

        self._service.execute(f"sbio_e = getdose({self.var},{to_matlab_string(name)});")
        if self._service.execute("isempty(sbio_e)", nargout=1):
            raise ElementNotFoundError(f"No dose named {name!r} in model {self.name!r}.")
        dose_type = "schedule" if "Schedule" in str(self._service.execute("class(sbio_e)", nargout=1)) else "repeat"
        detail: dict[str, Any] = {
            "Name": self._service.execute("sbio_e.Name", nargout=1),
            "Type": dose_type,
            "TargetName": self._service.execute("sbio_e.TargetName", nargout=1),
        }
        fields = ("Time", "Amount", "Rate") if dose_type == "schedule" else ("Amount", "StartTime", "Interval", "RepeatCount", "Rate")
        for attr in fields:
            detail[attr] = _finite_or_none(self._service.execute(f"sbio_e.{attr}", nargout=1))
        for attr in ("AmountUnits", "RateUnits", "TimeUnits"):
            detail[attr] = self._service.execute(f"sbio_e.{attr}", nargout=1)
        return detail

    def get_variant(self, name: str) -> dict[str, Any]:
        """Return a variant's Active flag and content entries."""

        self._service.execute(f"sbio_e = getvariant({self.var},{to_matlab_string(name)});")
        if self._service.execute("isempty(sbio_e)", nargout=1):
            raise ElementNotFoundError(f"No variant named {name!r} in model {self.name!r}.")
        return {
            "Name": self._service.execute("sbio_e.Name", nargout=1),
            "Active": self._service.execute("sbio_e.Active", nargout=1),
            "Content": self._service.execute("sbio_e.Content", nargout=1),
        }

    # --- builders: return a MATLAB command string (do not execute) ---
    def add_species_cmd(self, compartment: str, name: str, amount: float, units: str | None = None) -> str:
        command = f"addspecies({self._select('compartment', compartment)},{to_matlab_string(name)},{to_matlab_number(amount)});"
        return command if units is None else f"sbio_e = {command} sbio_e.InitialAmountUnits = {to_matlab_string(units)};"

    def add_reaction_cmd(self, name: str, equation: str) -> str:
        reaction, rate = _split_reaction_spec(equation)
        command = f"rxnObj = addreaction({self.var},{to_matlab_string(reaction)}); set(rxnObj,'Name',{to_matlab_string(name)});"
        return command if rate is None else f"{command} rxnObj.ReactionRate = {_format_reaction_rate(rate)};"

    def add_compartment_cmd(self, name: str, capacity: float = 1.0, units: str | None = None) -> str:
        command = f"addcompartment({self.var},{to_matlab_string(name)});"
        if capacity == 1.0 and units is None:
            return command
        updates: list[str] = []
        if capacity != 1.0:
            updates.append(f"sbio_e.Capacity = {to_matlab_number(capacity)};")
        if units is not None:
            updates.append(f"sbio_e.CapacityUnits = {to_matlab_string(units)};")
        return f"sbio_e = {command} {' '.join(updates)}"

    def add_parameter_cmd(self, name: str, value: float, units: str | None = None) -> str:
        command = f"addparameter({self.var},{to_matlab_string(name)},{to_matlab_number(value)});"
        return command if units is None else f"sbio_e = {command} sbio_e.ValueUnits = {to_matlab_string(units)};"

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

    # --- builders: doses and variants (getdose/getvariant path, not sbioselect) ---
    def add_dose_cmd(
        self,
        name: str,
        target: str,
        dose_type: str = "repeat",
        amount: float | None = None,
        start_time: float | None = None,
        interval: float | None = None,
        repeat_count: float | None = None,
        rate: float | None = None,
        amount_units: str | None = None,
        rate_units: str | None = None,
        time_units: str | None = None,
        times: list[float] | None = None,
        amounts: list[float] | None = None,
        rates: list[float] | None = None,
    ) -> str:
        """Build ``adddose`` plus assignments for each provided (non-None) field."""

        if dose_type not in ("repeat", "schedule"):
            raise ValueError(f"dose_type must be 'repeat' or 'schedule', got {dose_type!r}.")
        if dose_type == "schedule" and any(v is not None for v in (amount, rate, start_time, interval, repeat_count)):
            raise ValueError("amount/rate/start_time/interval/repeat_count are repeat-dose fields; " "a schedule dose uses amounts/rates.")
        if dose_type == "repeat" and any(v is not None for v in (times, amounts, rates)):
            raise ValueError("times/amounts/rates are schedule-dose fields, not valid for dose_type='repeat'.")
        vectors = [v for v in (times, amounts, rates) if v is not None]
        if vectors and any(len(v) != len(vectors[0]) for v in vectors):
            raise ValueError("times/amounts/rates must all have the same length.")

        parts = [
            f"sbio_d = adddose({self.var},{to_matlab_string(name)},{to_matlab_string(dose_type)});",
            f"sbio_d.TargetName = {to_matlab_string(target)};",
        ]
        for attr, value in (("Amount", amount), ("StartTime", start_time), ("Interval", interval), ("RepeatCount", repeat_count), ("Rate", rate)):
            if value is not None:
                parts.append(f"sbio_d.{attr} = {to_matlab_number(value)};")
        for attr, values in (("Time", times), ("Amount", amounts), ("Rate", rates)):
            if values is not None:
                parts.append(f"sbio_d.{attr} = {_matlab_column(values)};")
        for attr, value in (("AmountUnits", amount_units), ("RateUnits", rate_units), ("TimeUnits", time_units)):
            if value is not None:
                parts.append(f"sbio_d.{attr} = {to_matlab_string(value)};")
        return " ".join(parts)

    def set_dose_cmd(self, name: str, **fields: Any) -> str:
        """Build assignments updating a dose selected by ``getdose`` (KeyError on unknown)."""

        updates = [f"sbio_e = getdose({self.var},{to_matlab_string(name)});"]
        for field, value in fields.items():
            key = field.lower()
            if key not in _DOSE_FIELDS:
                raise KeyError(f"Unsupported dose field: {field}")
            formatted = to_matlab_string(value) if key in _DOSE_STRING_FIELDS else to_matlab_number(value)
            updates.append(f"sbio_e.{_DOSE_FIELDS[key]} = {formatted};")
        return " ".join(updates)

    def delete_dose_cmd(self, name: str) -> str:
        return f"delete(getdose({self.var},{to_matlab_string(name)}));"

    def add_variant_cmd(self, name: str, content: list[dict[str, Any]]) -> str:
        """Build ``addvariant`` plus ``addcontent`` for the given content entries."""

        command = f"sbio_v = addvariant({self.var},{to_matlab_string(name)});"
        if content:
            command += f" addcontent(sbio_v,{_matlab_content(content)});"
        return command

    def set_variant_cmd(self, name: str, content: list[dict[str, Any]]) -> str:
        """Build a command replacing a variant's entire Content."""

        return f"sbio_e = getvariant({self.var},{to_matlab_string(name)}); " f"sbio_e.Content = {_matlab_content(content)};"

    def delete_variant_cmd(self, name: str) -> str:
        return f"delete(getvariant({self.var},{to_matlab_string(name)}));"

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
            elif key == "rate":
                value = _format_reaction_rate(str(value))
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
            settings["AbsoluteTolerance"] = self._service.execute("sbio_cs.SolverOptions.AbsoluteTolerance", nargout=1)
            settings["RelativeTolerance"] = self._service.execute("sbio_cs.SolverOptions.RelativeTolerance", nargout=1)
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

    def _name_array(self, getter: str, names: list[str] | None) -> str:
        """Build a MATLAB array of ``getdose``/``getvariant`` selections, or ``[]``."""

        if not names:
            return "[]"
        return "[" + ",".join(f"{getter}({self.var},{to_matlab_string(name)})" for name in names) + "]"

    def _require_named(self, kind: str, existing: list[str], requested: list[str]) -> None:
        """Raise ``ElementNotFoundError`` if any requested name is not in ``existing``."""

        missing = [name for name in requested if name not in existing]
        if missing:
            raise ElementNotFoundError(f"No {kind}(s) {missing} in model {self.name!r}.")

    def _simulate_to_workspace(
        self,
        species: list[str] | None = None,
        doses: list[str] | None = None,
        variants: list[str] | None = None,
    ) -> str:
        """Run ``sbiosimulate`` on the active configset, leaving the result in a
        MATLAB variable, and return that variable's name.

        Named ``doses`` and/or ``variants`` are applied explicitly through the
        4-arg ``sbiosimulate`` (variants before doses), regardless of their
        Active flag. If ``species`` is given, the result is narrowed to those
        quantities via ``selectbyname``. Shared by :meth:`simulate` and the
        export helpers so every path simulates identically.
        """

        if doses:
            self._require_named("dose", self.doses(), doses)
        if variants:
            self._require_named("variant", self.variants(), variants)
        if doses or variants:
            variant_array = self._name_array("getvariant", variants)
            dose_array = self._name_array("getdose", doses)
            self._service.execute(f"sbio_sd = sbiosimulate({self.var},getconfigset({self.var})," f"{variant_array},{dose_array});")
        else:
            self._service.execute(f"sbio_sd = sbiosimulate({self.var});")
        if species:
            names_cell = "{" + ",".join(to_matlab_string(s) for s in species) + "}"
            self._service.execute(f"sbio_sd_sel = selectbyname(sbio_sd,{names_cell});")
            return "sbio_sd_sel"
        return "sbio_sd"

    def simulate(
        self,
        species: list[str] | None = None,
        doses: list[str] | None = None,
        variants: list[str] | None = None,
    ) -> dict[str, Any]:
        """Run ``sbiosimulate`` on the active configset and return time-course data.

        If ``species`` is given, only those quantities are returned (via
        ``selectbyname``) instead of every logged state. Named ``doses`` and/or
        ``variants`` are applied explicitly through the 4-arg ``sbiosimulate``
        (variants before doses), regardless of their Active flag.
        """

        source = self._simulate_to_workspace(species, doses, variants)
        time = self._service.execute(f"{source}.Time", nargout=1)
        data = self._service.execute(f"{source}.Data", nargout=1)
        names = self._service.execute(f"{source}.DataNames", nargout=1)
        units = self._service.execute(f"{source}.TimeUnits", nargout=1)
        return _format_simdata(time, data, names, units)

    def export_plot(
        self,
        path: str,
        resolution: int = 300,
        species: list[str] | None = None,
        doses: list[str] | None = None,
        variants: list[str] | None = None,
        title: str | None = None,
        x_label: str | None = None,
        y_label: str | None = None,
        legend_labels: list[str] | None = None,
    ) -> dict[str, Any]:
        """Simulate (honoring ``doses``/``variants``/``species``) and write the
        SimBiology plot to ``path`` as a PNG at the given ``resolution`` (DPI).

        Reuses :meth:`_simulate_to_workspace`, so the exported figure reflects
        exactly the same run ``simulate`` would produce for the same arguments.
        """

        source = self._simulate_to_workspace(species, doses, variants)
        names = self._service.execute(f"{source}.DataNames", nargout=1)
        names = [names] if isinstance(names, str) else [str(name) for name in names]
        if legend_labels is not None and len(legend_labels) != len(names):
            raise ValueError("legend_labels must match the number of plotted series.")
        self._service.execute(f"sbio_ax = sbioplot({source});")
        if title is not None:
            self._service.execute(f"title(sbio_ax,{to_matlab_string(title)});")
        if x_label is not None:
            self._service.execute(f"xlabel(sbio_ax,{to_matlab_string(x_label)});")
        if y_label is not None:
            self._service.execute(f"ylabel(sbio_ax,{to_matlab_string(y_label)});")
        if legend_labels is not None:
            self._service.execute(f"legend(sbio_ax,{_matlab_string_cell(legend_labels)});")
        self._service.execute("sbio_fig = get(sbio_ax,'Parent');")
        try:
            self._service.execute(f"exportgraphics(sbio_fig,{to_matlab_string(str(path))}," f"'Resolution',{int(resolution)});")
        finally:
            # Always close the figure sbioplot opened: a long-lived MCP session
            # would otherwise leak a window per export and slow MATLAB down.
            self._service.execute("close(sbio_fig);")
        return {"path": str(path), "resolution": int(resolution)}
