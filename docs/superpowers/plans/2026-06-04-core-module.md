# core/ Module Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `core/` — `SbioService` (session) and `SbioModel` (model gateway) — over the existing `MatlabLayer`, so tools can load/save SimBiology projects and read/build model elements.

**Architecture:** `tools -> core -> engine(MatlabLayer) -> MATLAB`. Core never imports `matlab.engine`. `SbioService` owns the session (load/save/discover); `SbioModel` reads elements and builds (does not execute) mutation commands. Spec: `docs/superpowers/specs/2026-06-04-core-module-design.md`.

**Tech Stack:** Python 3.12, MATLAB R2025b engine (`matlabengine 25.2`), SimBiology, pytest. Run all Python via `.venv` with `PYTHONPATH=<repo root>`.

**Verified against the live engine (probe results baked into the code below):**
- Discover models with `sbioroot().Models` (parens required after the function call before dot-indexing); `sbioreset;` clears the session for a clean load.
- MATLAB variable names must NOT start with an underscore (`sbio_e`, `sbio_model_1` are valid; `__e` is a parse error).
- `eng.eval` runs multi-statement strings only with `nargout=0`; returning a value (`nargout=1`) needs a single expression. So detail lookups are two calls.
- Name-list `{m.Species.Name}` -> Python `list[str]`; empty -> `[]`. `struct(...)` -> Python `dict`. Verified property names: species `Value`/`InitialAmountUnits`/`Parent.Name`; compartment `Capacity`/`CapacityUnits`; parameter `Value`/`ValueUnits`; reaction `Reaction`/`Reversible`.

**Test note:** Tests are real integration tests (no mocks). They share one engine via a session-scoped fixture (engine start ~30s, once per run). Run with:
`cd <repo> && source .venv/bin/activate && PYTHONPATH=$PWD pytest tests/ -v`

---

### Task 1: Custom exceptions

**Files:**
- Modify: `engine/exceptions.py` (currently empty)

- [ ] **Step 1: Write `engine/exceptions.py`**

```python
"""Custom error types for the SimBiology core layer.

Core raises these for precondition failures *before* touching MATLAB. Genuine
MATLAB failures keep propagating from MatlabLayer as RuntimeError.
"""


class SbioError(Exception):
    """Base class for all errors raised by the SimBiology core layer."""


class ProjectNotLoadedError(SbioError):
    """A session or model operation ran before a project was loaded."""


class ModelNotFoundError(SbioError):
    """A requested model name is missing, or get_model(None) is ambiguous."""


class ElementNotFoundError(SbioError):
    """A named species/reaction/compartment/parameter does not exist."""
```

- [ ] **Step 2: Verify it imports**

Run: `cd <repo> && source .venv/bin/activate && PYTHONPATH=$PWD python -c "from engine.exceptions import SbioError, ProjectNotLoadedError, ModelNotFoundError, ElementNotFoundError; print('ok')"`
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add engine/exceptions.py && git commit -m "feat(core): add SimBiology error types"
```

---

### Task 2: SbioModel — reads and builders

**Files:**
- Create/replace: `core/sbio_model.py` (currently empty)

`SbioModel` is constructed by `SbioService.get_model`. It holds the service, the MATLAB workspace var, and the model name. Module-level MATLAB-formatting helpers live here (no import cycle: this module never imports `sbio_service`).

- [ ] **Step 1: Write `core/sbio_model.py`**

```python
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
```

- [ ] **Step 2: Verify it imports**

Run: `PYTHONPATH=$PWD python -c "from core.sbio_model import SbioModel, _ml_str; print(_ml_str(\"a'b\"))"`
Expected: `'a''b'`

- [ ] **Step 3: Commit**

```bash
git add core/sbio_model.py && git commit -m "feat(core): add SbioModel gateway (reads + builders)"
```

---

### Task 3: SbioService — the session

**Files:**
- Replace: `core/sbio_service.py` (currently starts its own engine — remove that)

- [ ] **Step 1: Write `core/sbio_service.py`**

```python
"""The SimBiology session: load/save a .sbproj, discover and hand out models.

Routes every MATLAB call through the singleton MatlabLayer (never imports
matlab.engine directly), preserving the one-engine guarantee.
"""
from engine.matlab_layer import MatlabLayer
from engine.exceptions import ProjectNotLoadedError, ModelNotFoundError
from core.sbio_model import SbioModel, _ml_str


class SbioService:
    def __init__(self):
        MatlabLayer.launch()
        self.project_path = None
        self._models = {}   # model name -> MATLAB workspace var

    def load_project(self, path):
        """Load a .sbproj, return the names of the models it contains."""
        self.execute("sbioreset;")                       # clean session
        self.execute(f"sbioloadproject({_ml_str(path)})")
        count = int(self.execute("numel(sbioroot().Models)", nargout=1))
        self._models = {}
        for i in range(1, count + 1):
            var = f"sbio_model_{i}"
            self.execute(f"{var} = sbioroot().Models({i});")
            name = self.execute(f"{var}.Name", nargout=1)
            self._models[str(name)] = var
        self.project_path = path
        return list(self._models.keys())

    def save_project(self, path=None):
        """Persist the loaded models. Defaults to the loaded path (overwrite)."""
        target = path or self.project_path
        if target is None:
            raise ProjectNotLoadedError("No project loaded; nothing to save.")
        var_args = "".join(f",'{v}'" for v in self._models.values())
        self.execute(f"sbiosaveproject({_ml_str(target)}{var_args})")

    def model_names(self):
        return list(self._models.keys())

    def get_model(self, name=None):
        if not self._models:
            raise ProjectNotLoadedError("No project loaded.")
        if name is None:
            if len(self._models) != 1:
                raise ModelNotFoundError(
                    f"Specify a model name; loaded: {list(self._models)}")
            name = next(iter(self._models))
        if name not in self._models:
            raise ModelNotFoundError(
                f"No model named {name!r}; loaded: {list(self._models)}")
        return SbioModel(self, self._models[name], name)

    def execute(self, command, nargout=0):
        """Run a model-scoped MATLAB command through the engine."""
        return MatlabLayer.execute(command, nargout)
```

- [ ] **Step 2: Verify it imports**

Run: `PYTHONPATH=$PWD python -c "from core.sbio_service import SbioService; print('ok')"`
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add core/sbio_service.py && git commit -m "feat(core): add SbioService session over MatlabLayer"
```

---

### Task 4: Integration tests (real engine)

**Files:**
- Create: `tests/conftest.py`
- Create: `tests/test_core.py`

- [ ] **Step 1: Write `tests/conftest.py`**

```python
"""Shared fixtures: one engine per session; a saved sample project."""
import pytest
from engine.matlab_layer import MatlabLayer


@pytest.fixture(scope="session", autouse=True)
def _engine():
    MatlabLayer.launch()
    yield
    MatlabLayer.exit()


@pytest.fixture(scope="session")
def sample_project(tmp_path_factory):
    """Build a small model and save it as a .sbproj; return the path."""
    path = str(tmp_path_factory.mktemp("proj") / "demo.sbproj")
    e = MatlabLayer.execute
    e("sbioreset;")
    e("m=sbiomodel('demo'); c=addcompartment(m,'cell'); "
      "addspecies(c,'glucose',10); addspecies(c,'lactate',0); "
      "addparameter(m,'k1',1.5); r=addreaction(m,'glucose -> lactate'); "
      "r.Name='glycolysis';")
    e(f"sbiosaveproject('{path}','m');")
    return path
```

- [ ] **Step 2: Write `tests/test_core.py`**

```python
import pytest
from core.sbio_service import SbioService
from core.sbio_model import SbioModel
from engine.exceptions import (
    ProjectNotLoadedError, ModelNotFoundError, ElementNotFoundError)


def _loaded(sample_project):
    svc = SbioService()
    svc.load_project(sample_project)
    return svc


# --- SbioService ---
def test_load_returns_model_names(sample_project):
    assert SbioService().load_project(sample_project) == ["demo"]

def test_model_names_cached(sample_project):
    assert _loaded(sample_project).model_names() == ["demo"]

def test_get_model_single(sample_project):
    m = _loaded(sample_project).get_model()
    assert isinstance(m, SbioModel) and m.name == "demo"

def test_get_model_unknown_raises(sample_project):
    with pytest.raises(ModelNotFoundError):
        _loaded(sample_project).get_model("nope")

def test_get_model_before_load_raises():
    with pytest.raises(ProjectNotLoadedError):
        SbioService().get_model()

def test_save_before_load_raises():
    with pytest.raises(ProjectNotLoadedError):
        SbioService().save_project()


# --- SbioModel reads ---
def test_species_list(sample_project):
    assert _loaded(sample_project).get_model().species() == ["glucose", "lactate"]

def test_reactions_compartments_parameters(sample_project):
    m = _loaded(sample_project).get_model()
    assert m.reactions() == ["glycolysis"]
    assert m.compartments() == ["cell"]
    assert m.parameters() == ["k1"]

def test_get_species_detail(sample_project):
    m = _loaded(sample_project).get_model()
    assert m.get_species("glucose") == {
        "Name": "glucose", "Value": 10.0, "Units": "", "Compartment": "cell"}

def test_get_species_unknown_raises(sample_project):
    with pytest.raises(ElementNotFoundError):
        _loaded(sample_project).get_model().get_species("nope")


# --- SbioModel builders ---
def test_builder_returns_string_without_executing(sample_project):
    m = _loaded(sample_project).get_model()
    assert m.add_compartment_cmd("nucleus") == f"addcompartment({m.var},'nucleus');"
    assert m.compartments() == ["cell"]   # builder did not execute

def test_add_species_via_builder_and_persist(sample_project, tmp_path):
    svc = _loaded(sample_project)
    m = svc.get_model()
    svc.execute(m.add_species_cmd("cell", "atp", 5))
    assert "atp" in m.species()
    out = str(tmp_path / "out.sbproj")
    svc.save_project(out)
    assert "atp" in SbioService().load_project(out) or \
        "atp" in _loaded(out).get_model().species()
```

- [ ] **Step 3: Run the suite**

Run: `cd <repo> && source .venv/bin/activate && PYTHONPATH=$PWD pytest tests/test_core.py -v`
Expected: all tests PASS (first run is slow — one engine start).

- [ ] **Step 4: Commit**

```bash
git add tests/conftest.py tests/test_core.py && git commit -m "test(core): real-engine integration tests for SbioService/SbioModel"
```

---

### Task 5: Full verification

- [ ] **Step 1: Run the whole test directory** (includes existing `tests/test_matlab_layer.py`)

Run: `cd <repo> && source .venv/bin/activate && PYTHONPATH=$PWD pytest tests/ -v`
Expected: all PASS.

- [ ] **Step 2: Confirm no `matlab.engine` import leaked into core**

Run: `grep -rn "import matlab" core/ || echo "clean"`
Expected: `clean`

---

## Self-review

- **Spec coverage:** SbioService (load/save/model_names/get_model/execute) — Task 3 ✓. SbioModel (4 reads, 4 details, 4 builders) — Task 2 ✓. Exceptions — Task 1 ✓. Real-engine tests — Tasks 4-5 ✓. Dependency rule (no `matlab.engine` in core) — enforced by Task 5 Step 2 ✓.
- **Placeholders:** none — every step has complete, probe-verified code.
- **Type consistency:** `SbioService.execute(command, nargout=0)` used identically by `SbioModel`; `var`/`name` attributes consistent across model + tests; builder string in the test matches `add_compartment_cmd` exactly.
- **Known acceptable simplifications:** `add_reaction_cmd` leaves `r`, and `_detail` leaves `sbio_e`, in the MATLAB workspace (harmless temp vars). `load_project` calls `sbioreset` (one-project-at-a-time, per spec).
