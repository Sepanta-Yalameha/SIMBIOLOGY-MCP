"""Gateway to one SimBiology model: read elements, build mutation commands.

Reads execute through the service and marshal MATLAB -> Python. Builders only
return a MATLAB command string; tools run them via service.execute and then save.
"""
from engine.exceptions import ElementNotFoundError


def _ml_str(value):
    """Format a Python value as a single-quoted MATLAB string literal."""
    return "'" + str(value).replace("'", "''") + "'"


def _ml_num(value):
    """Format a Python number as a MATLAB numeric literal."""
    return repr(float(value))


# struct() field expressions per element type; `sbio_e` is the selected element.
_DETAIL = {
    "species": "struct('Name',sbio_e.Name,'Value',sbio_e.Value,"
               "'Units',sbio_e.InitialAmountUnits,'Compartment',sbio_e.Parent.Name)",
    "reaction": "struct('Name',sbio_e.Name,'Reaction',sbio_e.Reaction,"
                "'Reversible',sbio_e.Reversible)",
    "compartment": "struct('Name',sbio_e.Name,'Capacity',sbio_e.Capacity,"
                   "'Units',sbio_e.CapacityUnits)",
    "parameter": "struct('Name',sbio_e.Name,'Value',sbio_e.Value,"
                 "'Units',sbio_e.ValueUnits)",
}


class SbioModel:
    def __init__(self, service, var, name):
        self._service = service
        self.var = var      # MATLAB workspace variable holding the model
        self.name = name

    # --- reads: element name lists ---
    def species(self):
        return self._names("Species")

    def reactions(self):
        return self._names("Reactions")

    def compartments(self):
        return self._names("Compartments")

    def parameters(self):
        return self._names("Parameters")

    def _names(self, prop):
        result = self._service.execute(f"{{{self.var}.{prop}.Name}}", nargout=1)
        return [str(x) for x in (result or [])]

    # --- reads: element details ---
    def get_species(self, name):
        return self._detail("species", name)

    def get_reaction(self, name):
        return self._detail("reaction", name)

    def get_compartment(self, name):
        return self._detail("compartment", name)

    def get_parameter(self, name):
        return self._detail("parameter", name)

    def _detail(self, kind, name):
        select = (f"sbioselect({self.var},'Type',{_ml_str(kind)},"
                  f"'Name',{_ml_str(name)})")
        self._service.execute(f"sbio_e = {select};")          # nargout=0
        if self._service.execute("isempty(sbio_e)", nargout=1):
            raise ElementNotFoundError(
                f"No {kind} named {name!r} in model {self.name!r}.")
        return self._service.execute(_DETAIL[kind], nargout=1)  # single expr

    # --- builders: return a MATLAB command string (do NOT execute) ---
    def add_species_cmd(self, compartment, name, amount):
        comp = (f"sbioselect({self.var},'Type','compartment',"
                f"'Name',{_ml_str(compartment)})")
        return f"addspecies({comp},{_ml_str(name)},{_ml_num(amount)});"

    def add_reaction_cmd(self, name, equation):
        return (f"r=addreaction({self.var},{_ml_str(equation)}); "
                f"r.Name={_ml_str(name)};")

    def add_compartment_cmd(self, name):
        return f"addcompartment({self.var},{_ml_str(name)});"

    def add_parameter_cmd(self, name, value):
        return f"addparameter({self.var},{_ml_str(name)},{_ml_num(value)});"
