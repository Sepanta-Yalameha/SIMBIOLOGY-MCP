"""Gateway to a single SimBiology model.

Reads execute through the owning service and marshal MATLAB results into Python
types. Builders only return a MATLAB command string; the caller runs it via the
service and persists the change.
"""

from __future__ import annotations

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
        return command if rate is None else f"{command} rxnObj.ReactionRate = {to_matlab_string(rate)};"

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
