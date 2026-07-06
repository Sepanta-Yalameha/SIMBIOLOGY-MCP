# AGENTS.md

Developer-facing context for the `SIMBIOLOGY-MCP` repo.

This file is for people changing the codebase, not for end users calling the MCP.

## What This Repo Is

`SIMBIOLOGY-MCP` is a Python MCP server that exposes MATLAB SimBiology operations as MCP tools.

The repo has two jobs:

1. Keep one long-lived MATLAB Engine session alive.
2. Translate MCP tool calls into MATLAB/SimBiology commands and return JSON-safe Python data.

The server is intentionally thin. Most behavior is simple string-building around MATLAB commands, not a large Python domain model.

## Mental Model

The runtime flow is:

`FastMCP tool call -> tools/* -> core.sbio_service.SbioService -> core.sbio_model.SbioModel -> engine.matlab_layer.MatlabLayer -> MATLAB Engine -> SimBiology`

Keep that layering intact:

- `interfaces/` wires the MCP server.
- `tools/` defines public MCP tools and light validation/echo behavior.
- `core/` owns SimBiology session state and MATLAB command builders/read paths.
- `engine/` is the only layer that should talk to `matlab.engine`.
- `external/` wraps non-MATLAB APIs like PubMed and iGEM.

If you are about to import `matlab.engine` outside `engine/`, that is probably the wrong place.

## Repo Layout

- `main.py`: tiny repo entry point, just calls `interfaces.mcp_server.run()`.
- `interfaces/mcp_server.py`: builds the `FastMCP` server from the shared tool registry.
- `tools/registry.py`: global tool registry via `@register(...)`.
- `tools/sbio_tools.py`: main SimBiology MCP tool surface.
- `tools/external_tools.py`: PubMed and iGEM MCP tools.
- `core/sbio_service.py`: project/session/model orchestration over the shared MATLAB engine.
- `core/sbio_model.py`: MATLAB command builders plus read/sim/export helpers for one model.
- `engine/matlab_layer.py`: singleton MATLAB Engine wrapper and exception mapping.
- `engine/exceptions.py`: app-level exception types.
- `external/pubmed.py`: thin HTTP/XML wrapper around NCBI eutils.
- `external/igem.py`: thin wrapper around `igem-registry-api`, with normalization.
- `scripts/setup.py`: installs MATLAB Engine for Python from a local MATLAB install.
- `setup_venv.ps1`: machine bootstrap script for Windows dev setup.
- `tests/`: split between hermetic unit tests and opt-in/live MATLAB/network tests.
- `SKILLS.md`: repo-level skill guidance; treat it as source of truth for agent usage behavior.
- `.agents/skills/simbiology/SKILLS.md`: domain guidance for how SimBiology should be used correctly.

## Runtime Architecture

### 1. Tool registration is import-driven

`tools/__init__.py` imports both `sbio_tools` and `external_tools`, and those modules self-register functions into `TOOLS` through `@register`.

That means:

- Adding a new MCP tool usually means adding one decorated function in `tools/sbio_tools.py` or `tools/external_tools.py`.
- The server will expose it automatically as long as the module is imported through `tools/__init__.py`.
- Tests verify that tools are registered and visible through `FastMCP`.

### 2. MATLAB startup is lazy at tool-use time

`interfaces.mcp_server.run()` checks that `matlab.engine` is importable, but it does not start MATLAB.

Actual MATLAB launch happens later:

- `tools.sbio_tools._svc()` creates `SbioService()` on first SimBiology tool use.
- `SbioService.__init__()` calls `MatlabLayer().launch()`.
- `MatlabLayer` is a singleton and reuses one engine process.

This keeps MCP startup fast and pushes MATLAB cost to first real use.

### 3. Service owns project state; model builds commands

`SbioService` owns:

- the loaded project path
- the loaded models map: model name -> MATLAB workspace variable
- high-level project/model lifecycle

`SbioModel` owns:

- read helpers for model contents
- string builders for mutations
- simulation/export helpers for one model variable

Rule of thumb:

- If logic is about "which model/project/session are we on?" it belongs in `SbioService`.
- If logic is "what MATLAB command should modify/read this model object?" it belongs in `SbioModel`.

### 4. Builders do not execute

Most `*_cmd()` methods in `core/sbio_model.py` return MATLAB command strings only.

Execution is separate and explicit:

- build command in `SbioModel`
- run command through `SbioService.execute()`

This is an important repo pattern and heavily tested. Do not quietly blur it unless there is a very strong reason.

## Important Behavioral Invariants

These matter more than style.

### One MATLAB gateway

All MATLAB calls should route through `MatlabLayer.execute()`. That keeps startup, liveness checks, and exception mapping centralized.

### JSON-safe results

Anything returned to MCP clients should be JSON-friendly.

Notable example:

- non-finite floats from MATLAB config (`Inf`, `NaN`) are normalized to `None` by `_finite_or_none()`

If you add a new read path, make sure it cannot leak MATLAB-native oddities into tool results.

### Default-until-asked behavior for SimBiology usage

The repo-level `SKILLS.md` and `.agents/skills/simbiology/SKILLS.md` define an important product rule:

- leave configurable simulation behavior at SimBiology defaults unless explicitly asked to change it
- do not silently "improve" solver/tolerance/logging settings

This is partly product behavior and partly a correctness guard.

### `MaximumNumberOfLogs` is not a display knob

This is called out in the skill docs because it is a real footgun.

Lowering `MaximumNumberOfLogs` truncates a run early. It is not just about output verbosity.

Do not optimize payload size by changing it. Use filtering of returned species or export shape instead.

### Doses and variants should be applied per simulation run when requested

`SbioModel._simulate_to_workspace()` uses named doses/variants via the 4-arg `sbiosimulate(...)` path.

Important consequences:

- simulation/export can honor doses and variants without mutating baseline active state
- tools like `simulate_model`, `export_graph`, and `export_csv` should stay behaviorally aligned

If you change simulation behavior, keep those three paths in sync.

### Export helpers must reflect the same run as simulate

`export_graph()` and `export_csv()` are expected to honor the same `species`, `doses`, and `variants` inputs as `simulate_model()`.

There are tests specifically guarding this.

### Figures must be closed after plot export

`SbioModel.export_plot()` closes the MATLAB figure in a `finally` block.

Do not remove that without replacing it with equivalent cleanup; this server is long-lived and MATLAB UI leaks accumulate.

## How The Main Tool Layer Works

`tools/sbio_tools.py` is intentionally repetitive. That is mostly a feature, not a bug.

Shared helpers:

- `_svc()`: shared lazy `SbioService`
- `_model()`: resolve selected model
- `_run()`: execute raw MATLAB command
- `_add()`: execute a builder and echo created fields
- `_modify()`: drop `None` fields, call the model setter, echo changed fields
- `_remove()`: execute delete builder and echo removed name
- `_require_units()`: reject blank units on create paths

The tool layer mainly does four things:

1. shape MCP schemas via typed Python function signatures
2. perform light validation
3. delegate to `core`
4. return small structured dicts/lists

Keep it boring. If adding a tool needs a lot of Python-side state, double-check whether it should really live in `core`.

## How Simulation/Mutation Actually Behave

### Projects and models

- `load_project()` does `sbioreset` first, then `sbioloadproject(...)`.
- `create_project()` does `sbioreset`, creates one fresh model, and optionally saves immediately.
- `save_project()` writes parent directories if needed.
- `get_model(None)` only works when exactly one model is loaded; otherwise it raises `ModelNotFoundError`.

### Model indexing

Loaded models are stored as MATLAB variable names like `sbio_model_1`, `sbio_model_2`, etc.

This is simple and good enough. If you rename a model, the workspace variable stays the same and only the name map changes.

### Species/compartments/parameters

Create paths require non-blank units. That is deliberate and tested.

### Reactions

The tool API uses structured inputs:

- `left`
- `right`
- `reversible`
- optional `rate`

Those are converted into SimBiology-compatible reaction strings by `build_reaction_equation()` and friends.

One past regression is explicitly guarded:

- `modify_reaction()` must not wipe stoichiometry when only `rate` or `reversible` changes

Do not reintroduce that by rebuilding reaction text unconditionally.

### Doses

There are two supported dose forms:

- `repeat`
- `schedule`

Validation is intentionally minimal but important:

- repeat-only scalar fields are rejected on schedule doses
- schedule vector fields are rejected on repeat doses
- schedule vectors must have matching lengths

`modify_dose()` only supports repeat-dose scalar field edits. Schedule dose vector edits are currently "remove and recreate".

### Variants

Variant `content` is a list of dicts with:

- `type`
- `name`
- `property`
- `value`

`modify_variant()` replaces the entire content and rejects empty content.

That replacement behavior is intentional. Empty content would silently wipe the variant, so deletion is a separate operation.

## External API Layer

The non-MATLAB APIs are intentionally thin wrappers.

### PubMed

- Uses `httpx.get(...)` directly.
- Parses XML with stdlib `xml.etree.ElementTree`.
- Optionally injects `NCBI_API_KEY` from `.env`.

This is not a generic NCBI client. Keep it simple unless requirements change.

### iGEM

- Uses `igem-registry-api`.
- Caches a connected client with `@lru_cache(maxsize=1)`.
- Normalizes slug/UUID lookup and returns flattened JSON-ish dicts.

The split between `igem_part()` and `igem_search()` is deliberate:

- `igem_part()` is exact lookup only
- free-text goes through search

Tests guard that free-text is rejected on exact lookup.

## Testing Strategy

The repo has a clean split:

- hermetic unit tests: no MATLAB, no network
- MATLAB integration tests: `@pytest.mark.matlab`
- live network tests: `@pytest.mark.live`

### Default dev command

Use:

```powershell
python -m pytest -m "not matlab and not live"
```

That is the same contract described in the repo docs and CI intent.

### How test gating works

Repo-level `conftest.py`:

- auto-skips `matlab` tests when `matlab` is not importable
- auto-skips `live` tests unless `--run-live` is passed
- stubs `igem_registry_api` in `sys.modules` so unit tests can import code without the real dependency present

### Integration fixtures

`tests/core/conftest.py` creates real temporary `.sbproj` fixtures through MATLAB:

- `sample_project`
- `simulatable_project`
- `two_model_project`

These fixtures define what the core layer is expected to support in practice. When changing model/session behavior, read them first.

## Setup and Packaging

### Python packaging

This is a flat-layout setuptools project with explicit packages in `pyproject.toml`.

Console scripts:

- `simbiology-mcp` -> `interfaces.mcp_server:run`
- `simbiology-mcp-setup` -> `scripts.setup:main`

### Dependency intent

`pyproject.toml` keeps only direct runtime dependencies.

`requirements.txt` and `setup_venv.ps1` are used for pinned/reproducible environment setup.

Do not casually duplicate dependency declarations in multiple places without understanding which workflow they serve.

### MATLAB Engine installation

The MATLAB Engine Python package is special here.

This repo prefers installing it from the local MATLAB installation, not from PyPI, because the version must match the installed MATLAB release.

`scripts/setup.py`:

- locates MATLAB
- finds `extern/engines/python`
- installs build prerequisites with `uv`
- runs MATLAB's own `setup.py` in place

If a user reports engine install pain on Windows, start there.

## When Editing This Repo

### Good places to add behavior

- new MCP tool: usually `tools/sbio_tools.py`
- new MATLAB builder/read helper: usually `core/sbio_model.py`
- new project/model orchestration: usually `core/sbio_service.py`
- new server wiring behavior: `interfaces/mcp_server.py`
- new external API wrapper: `external/*` plus `tools/external_tools.py`

If you add, remove, or materially change an MCP tool, update the `README.md` tools section in the same change so the public surface stays documented.

### Things to preserve

- lazy MATLAB startup
- singleton MATLAB engine
- builder-vs-execute split
- JSON-safe tool outputs
- alignment between `simulate_model`, `export_graph`, and `export_csv`
- explicit tests for regressions around doses, variants, exports, and reaction edits

### Things not to overbuild

- no extra abstraction around single-path tool functions
- no generic ORM-style layer over SimBiology
- no second command execution path bypassing `MatlabLayer`
- no heavy API client framework for PubMed/iGEM unless requirements justify it

The repo is healthiest when it stays as a thin adapter.

## Known Sharp Edges

- `FastMCP` server construction depends on import side effects from `tools/__init__.py`.
- MATLAB errors are mapped partly by matching message text; be careful changing that logic.
- Some MATLAB properties differ by solver type, especially solver tolerances for stochastic solvers.
- Model ambiguity is intentional: if more than one model is loaded, callers must specify the model name.
- `export_csv()` returns inline CSV when no path is given, but writes to disk and returns metadata when `path` is provided.

## Source Of Truth Priority

When repo docs disagree, use this order:

1. tests
2. current code
3. `SKILLS.md`
4. `README.md`

For model-usage correctness rules, also read:

- `.agents/skills/simbiology/SKILLS.md`

That file captures product/domain expectations that are easy to miss if you only read the Python code.
