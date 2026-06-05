# core/ Module Design — SbioService + SbioModel

Date: 2026-06-04
Status: Approved (design); implementation pending
Scope owner: this team owns `core/`. `engine/` (MatlabLayer) is a given dependency.

## Overview

`core/` is the SimBiology-session layer. It sits between the tools (agent-facing verbs) and the
engine (the one MATLAB process). It provides two cohesive units:

- `SbioService` — owns the session: load/save a `.sbproj`, discover models, hand out model gateways.
- `SbioModel` — a gateway bound to one model: read its elements, build SimBiology mutation commands.

Core contains no tool logic. Tools orchestrate (decide, validate, save); core provides capabilities.

## Dependency direction (hard rule)

```
tools  ->  core (SbioService, SbioModel)  ->  engine (MatlabLayer)  ->  MATLAB
```

Core never imports `matlab.engine`. Every MATLAB interaction goes through `MatlabLayer`, preserving
the single-engine guarantee. (The current `core/sbio_service.py` starts its own engine; that is
replaced.)

## SbioService — the session

State: `project_path: str | None`, `_models: dict[str, str]` (model name -> MATLAB workspace var).

- `__init__()` — calls `MatlabLayer.launch()` (idempotent). Initializes empty state.
- `load_project(path) -> list[str]`
  - Emits `sbioloadproject('<path>')`, dropping saved variables into the workspace.
  - Discovers `SimBiology.Model` variables (the `whos` + class-filter approach proven in
    `proof_of_concept.py`), aliases each to a deterministic var `sbio_model_1`, `sbio_model_2`, …,
    and records `name -> var`.
  - Returns model names. Zero models -> `[]` (not an error). Bad path -> MatlabLayer raises, wrapped
    as `ProjectNotLoadedError`.
  - Rationale for aliasing: saved variable names are arbitrary/unknown; deterministic aliases give
    every later command a stable, collision-free handle. SimBiology models are handle objects, so the
    alias *is* the model — mutation through it and a later save persist the change.
- `save_project(path=None) -> None`
  - Defaults to the loaded path (overwrite in place); this is the crash-recovery hook.
  - Nothing loaded -> `ProjectNotLoadedError`.
  - Emits `sbiosaveproject('<path>', 'sbio_model_1', …)` for all bound model vars.
- `model_names() -> list[str]` — cached names from load; no MATLAB call.
- `get_model(name=None) -> SbioModel`
  - No project loaded -> `ProjectNotLoadedError`.
  - `None` + exactly one model -> that model; `None` + several -> `ModelNotFoundError` (ambiguous);
    unknown name -> `ModelNotFoundError`.
  - Returns `SbioModel(service=self, var=<sbio_model_N>, name=name)`. No MATLAB call.
- `execute(command, nargout=0)` — thin delegate to `MatlabLayer.execute`. The single channel tools
  use to run builder strings and model-scoped commands.

## SbioModel — gateway to one model

Constructed `(service, var, name)`. `var` is the `sbio_model_N` string; every command references it.

### Reads (execute + marshal MATLAB -> Python)

All four name-lists share one private helper; all four detail-lookups share another.

- `species() / reactions() / compartments() / parameters() -> list[str]`
  - Emits `{<var>.Species.Name}` (resp. `.Reactions`, `.Compartments`, `.Parameters`), `nargout=1`.
  - MATLAB cell of names -> Python `list[str]`. Empty model -> `[]`.
- `get_species(name) / get_reaction(name) / get_compartment(name) / get_parameter(name) -> dict`
  - Locate via `sbioselect(<var>,'Type','<type>','Name','<name>')`; empty -> `ElementNotFoundError`.
  - Build a MATLAB `struct(...)` of fields, return `nargout=1` -> Python `dict`. Fields per type:
    - species: `Name, Value (InitialAmount), Units, Compartment`
    - reaction: `Name, Reaction, Reversible`
    - compartment: `Name, Capacity, Units`
    - parameter: `Name, Value, Units`

### Builders (return a MATLAB command string; do NOT execute)

They encapsulate SimBiology syntax + `var`, so tools never hand-write MATLAB. A tool runs the string
via `service.execute(...)`, then calls `save_project()`.

- `add_species_cmd(compartment, name, amount)`
  -> `addspecies(sbioselect(<var>,'Type','compartment','Name','<compartment>'),'<name>',<amount>);`
- `add_reaction_cmd(name, equation)`
  -> `r=addreaction(<var>,'<equation>'); r.Name='<name>';`
- `add_compartment_cmd(name)` -> `addcompartment(<var>,'<name>');`
- `add_parameter_cmd(name, value)` -> `addparameter(<var>,'<name>',<value>);`

A private quoting helper escapes single quotes (`'` -> `''`) so names cannot break the command.

## engine/exceptions.py

- `SbioError(Exception)` — base for all core-raised errors.
- `ProjectNotLoadedError` — any session/model op before a successful `load_project`.
- `ModelNotFoundError` — `get_model` miss or ambiguous `None`.
- `ElementNotFoundError` — a `get_*` lookup that `sbioselect` returns empty for.

Semantics: core raises these for precondition failures *before* touching MATLAB; genuine MATLAB
errors keep propagating from `MatlabLayer` as `RuntimeError`. Clear split between "core used wrong"
and "MATLAB rejected the command."

## Testing — real integration (no mocks)

Tests run only once MATLAB is runnable (OS libs + license activation + Python engine installed).
Strategy: build a tiny model in-session (`sbiomodel` -> `addcompartment` -> `addspecies` ->
`addreaction`), `sbiosaveproject` to a temp `.sbproj`, then exercise `load_project` / `get_model` /
reads / builders against that real round-trip. No shipped fixtures, no mocks.

## Scope guards (YAGNI)

- One session, one loaded project at a time (matches one-session-per-engine decision).
- No events, rules, doses, or variants.
- No simulation logic in core (simulation is a tool that calls `sbiosimulate` via `service.execute`).
- Builders cover only the MVP element-adds. Adding more later mirrors "adding a tool is easy."

## Open items / to confirm against live engine

- Exact form of project load + model discovery (POC-proven path; may simplify to a struct-return
  form of `sbioloadproject` if available in R2025b).
- Field names for `get_*` details (`InitialAmount`, `Capacity`, etc.) verified against R2025b.
