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


# struct() field expressions per element type; ``sbio_e`` is the selected element.
_DETAIL: dict[str, str] = {
    "species": "struct('Name',sbio_e.Name,'Value',sbio_e.Value,"
               "'Units',sbio_e.InitialAmountUnits,'Compartment',sbio_e.Parent.Name)",
    "reaction": "struct('Name',sbio_e.Name,'Reaction',sbio_e.Reaction,"
                "'Reversible',sbio_e.Reversible)",
    "compartment": "struct('Name',sbio_e.Name,'Capacity',sbio_e.Capacity,"
                   "'Units',sbio_e.CapacityUnits)",
    "parameter": "struct('Name',sbio_e.Name,'Value',sbio_e.Value,"
                 "'Units',sbio_e.ValueUnits)",
}

_SETTERS: dict[str, dict[str, str]] = {
    "species": {
        "name": "sbio_e.Name = {value};",
        "value": "sbio_e.Value = {value};",
        "units": "sbio_e.InitialAmountUnits = {value};",
    },
    "reaction": {
        "name": "sbio_e.Name = {value};",
        "reaction": "sbio_e.Reaction = {value};",
        "reversible": "sbio_e.Reversible = {value};",
    },
    "compartment": {
        "name": "sbio_e.Name = {value};",
        "capacity": "sbio_e.Capacity = {value};",
        "units": "sbio_e.CapacityUnits = {value};",
    },
    "parameter": {
        "name": "sbio_e.Name = {value};",
        "value": "sbio_e.Value = {value};",
        "units": "sbio_e.ValueUnits = {value};",
    },
}


class SbioModel:
    """Read elements of one model and build SimBiology mutation commands."""

    def __init__(self, service: SbioService, var: str, name: str) -> None:
        self._service = service
        self.var = var      # MATLAB workspace variable holding the model
        self.name = name

    # --- reads: element name lists ---
    def species(self) -> list[str]:
        """Return the names of every species in the model."""

        return self._names("Species")

    def reactions(self) -> list[str]:
        """Return the names of every reaction in the model."""

        return self._names("Reactions")

    def compartments(self) -> list[str]:
        """Return the names of every compartment in the model."""

        return self._names("Compartments")

    def parameters(self) -> list[str]:
        """Return the names of every parameter in the model."""

        return self._names("Parameters")

    def _names(self, prop: str) -> list[str]:
        """Return the ``Name`` of every element under ``model.<prop>``."""

        result = self._service.execute(f"{{{self.var}.{prop}.Name}}", nargout=1)
        return [str(item) for item in (result or [])]

    # --- reads: element details ---
    def get_species(self, name: str) -> dict[str, Any]:
        """Return a species' fields as a dict."""

        return self._detail("species", name)

    def get_reaction(self, name: str) -> dict[str, Any]:
        """Return a reaction's fields as a dict."""

        return self._detail("reaction", name)

    def get_compartment(self, name: str) -> dict[str, Any]:
        """Return a compartment's fields as a dict."""

        return self._detail("compartment", name)

    def get_parameter(self, name: str) -> dict[str, Any]:
        """Return a parameter's fields as a dict."""

        return self._detail("parameter", name)

    def _detail(self, kind: str, name: str) -> dict[str, Any]:
        """Select one element by name and marshal its fields into a dict.

        Args:
            kind: SimBiology element type (``species``, ``reaction``, ...).
            name: Element name to look up.

        Returns:
            The element's fields as a dict.

        Raises:
            ElementNotFoundError: If no element of ``kind`` has that name.
        """

        select = (f"sbioselect({self.var},'Type',{to_matlab_string(kind)},"
                  f"'Name',{to_matlab_string(name)})")
        self._service.execute(f"sbio_e = {select};")
        if self._service.execute("isempty(sbio_e)", nargout=1):
            raise ElementNotFoundError(
                f"No {kind} named {name!r} in model {self.name!r}.")
        return self._service.execute(_DETAIL[kind], nargout=1)

    # --- builders: return a MATLAB command string (do not execute) ---
    def add_species_cmd(self, compartment: str, name: str, amount: float) -> str:
        """Build a command that adds a species to a compartment."""

        comp = (f"sbioselect({self.var},'Type','compartment',"
                f"'Name',{to_matlab_string(compartment)})")
        return f"addspecies({comp},{to_matlab_string(name)},{to_matlab_number(amount)});"

    def add_reaction_cmd(self, name: str, equation: str) -> str:
        """Build a command that adds a named reaction from an equation."""

        reaction, rate = _split_reaction_spec(equation)
        command = (
            f"rxnObj = addreaction({self.var},{to_matlab_string(reaction)}); "
            f"set(rxnObj,'Name',{to_matlab_string(name)});"
        )
        if rate is not None:
            command += f" rxnObj.ReactionRate = {to_matlab_string(rate)};"
        return command

    def add_compartment_cmd(self, name: str) -> str:
        """Build a command that adds a compartment."""

        return f"addcompartment({self.var},{to_matlab_string(name)});"

    def add_parameter_cmd(self, name: str, value: float) -> str:
        """Build a command that adds a parameter."""

        return f"addparameter({self.var},{to_matlab_string(name)},{to_matlab_number(value)});"

    def rename_model_cmd(self, new_name: str) -> str:
        """Build a command that renames the model."""

        return f"{self.var}.Name = {to_matlab_string(new_name)};"

    def delete_model_cmd(self) -> str:
        """Build a command that deletes the model from the root."""

        return f"delete({self.var});"

    def delete_species_cmd(self, name: str) -> str:
        """Build a command that deletes a species."""

        return self._delete_cmd("species", name)

    def delete_reaction_cmd(self, name: str) -> str:
        """Build a command that deletes a reaction."""

        return self._delete_cmd("reaction", name)

    def delete_compartment_cmd(self, name: str) -> str:
        """Build a command that deletes a compartment."""

        return self._delete_cmd("compartment", name)

    def delete_parameter_cmd(self, name: str) -> str:
        """Build a command that deletes a parameter."""

        return self._delete_cmd("parameter", name)

    def set_species_cmd(self, name: str, **fields: Any) -> str:
        """Build commands that update a species."""

        return self._set_cmd("species", name, fields)

    def set_reaction_cmd(self, name: str, **fields: Any) -> str:
        """Build commands that update a reaction."""

        return self._set_cmd("reaction", name, fields)

    def set_compartment_cmd(self, name: str, **fields: Any) -> str:
        """Build commands that update a compartment."""

        return self._set_cmd("compartment", name, fields)

    def set_parameter_cmd(self, name: str, **fields: Any) -> str:
        """Build commands that update a parameter."""

        return self._set_cmd("parameter", name, fields)

    def _delete_cmd(self, kind: str, name: str) -> str:
        select = (f"sbioselect({self.var},'Type',{to_matlab_string(kind)},"
                  f"'Name',{to_matlab_string(name)})")
        return f"delete({select});"

    def _set_cmd(self, kind: str, name: str, fields: dict[str, Any]) -> str:
        select = (f"sbioselect({self.var},'Type',{to_matlab_string(kind)},"
                  f"'Name',{to_matlab_string(name)})")
        updates: list[str] = [f"sbio_e = {select};"]
        for field, value in fields.items():
            key = field.lower()
            if key not in _SETTERS[kind]:
                raise KeyError(f"Unsupported {kind} field: {field}")
            formatted = self._format_field_value(kind, key, value)
            updates.append(_SETTERS[kind][key].format(value=formatted))
        return " ".join(updates)

    def _format_field_value(self, kind: str, field: str, value: Any) -> str:
        if field in {"name", "reaction", "units", "compartment"}:
            return to_matlab_string(value)
        if field == "reversible":
            return "true" if bool(value) else "false"
        return to_matlab_number(value)
