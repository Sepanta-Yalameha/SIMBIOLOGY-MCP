# SimBiology MCP Server

## Overview

The SimBiology MCP Server is a Model Context Protocol (MCP) interface for MATLAB SimBiology, enabling programmatic control of biological modeling and simulation workflows from AI agents and external tools.

It bridges large language model systems with MATLAB’s SimBiology toolbox through the MATLAB Engine for Python, allowing automated creation, modification, and execution of computational biology models.

---

## Purpose

SimBiology is a powerful environment for modeling biochemical and pharmacokinetic systems, but it is primarily MATLAB-driven and interactive.

This MCP server provides a structured programmatic layer that:

- Exposes SimBiology functionality as MCP tools
- Enables automated model construction and simulation
- Supports agent-driven workflows for systems biology
- Removes the need for manual MATLAB interaction

---

## Architecture

The system is divided into two layers:

### Setup Layer (Environment Bootstrap)

A PowerShell-based setup script that:

- Detects installed MATLAB versions via Windows registry
- Allows selection of MATLAB release
- Detects available Python interpreters
- Creates an isolated Python virtual environment
- Installs MATLAB Engine for Python using a stable legacy installation method
- Validates environment readiness

This layer is executed once per machine setup.

---

### Runtime Layer (MCP Server)

A Python-based MCP server that:

- Connects to MATLAB via the MATLAB Engine API
- Maintains a persistent MATLAB session
- Exposes SimBiology operations as MCP tools
- Executes simulations and returns structured outputs
- Supports iterative model modification workflows

---

## Features

- Programmatic creation of SimBiology models
- Reaction and species management
- Parameter configuration and updates
- Simulation execution through MATLAB Engine
- Retrieval of simulation results
- MCP-compatible tool interface for LLM integration
- Persistent MATLAB session management

---

## Example Use Cases

- Construct pharmacokinetic (PK/PD) models from natural language descriptions
- Simulate drug concentration over time
- Modify reaction rates and rerun simulations
- Build multi-compartment biological systems
- Automate sensitivity analysis workflows

---

## Requirements

- MATLAB R2024a or later
- SimBiology Toolbox installed
- Python 3.12 or later
- Windows operating system
- MCP-compatible runtime environment (e.g., VSCode MCP client or agent framework)

---

## Installation

Run the setup script from the project root. It detects your MATLAB and Python
installs, creates a `.venv`, installs the pinned dependencies from
`requirements.txt`, and installs the MATLAB Engine for Python that matches your
MATLAB release:

```powershell
.\setup_venv.ps1
```

To skip the interactive prompts, pass explicit indices or paths:

```powershell
.\setup_venv.ps1 -MatlabIndex 0 -PythonIndex 0
```

### Installing the server as a package (optional)

The project ships a `pyproject.toml`, so once the venv exists you can install the
server itself as an editable package. This puts its packages on the import path
(no need to set `PYTHONPATH`) and registers a `simbiology-mcp` command:

```powershell
.\.venv\Scripts\python.exe -m pip install -e .
```

---

## Usage

Start the server over stdio, either through the repo entry point or the installed
command:

```powershell
# from the repo, with the packages importable
$env:PYTHONPATH = (Get-Location).Path
.\.venv\Scripts\python.exe .\main.py

# or, after `pip install -e .`
simbiology-mcp
```

### Wiring into an MCP client

Point your MCP client at the server command. A typical stdio configuration:

```json
{
  "mcpServers": {
    "simbiology": {
      "command": "C:/path/to/SIMBIOLOGY-MCP/.venv/Scripts/python.exe",
      "args": ["C:/path/to/SIMBIOLOGY-MCP/main.py"],
      "env": { "PYTHONPATH": "C:/path/to/SIMBIOLOGY-MCP" }
    }
  }
}
```

The MATLAB engine starts lazily on the first tool call that needs it, so client
startup stays fast.

### External API keys

PubMed works without a key but is rate-limited. To raise the limit, copy
`.env.example` to `.env` and set `NCBI_API_KEY`.

---

## Tools

The server exposes its capabilities as MCP tools, grouped by area:

- **Projects:** `load_project`, `create_project`, `save_project`
- **Models:** `create_model`, `rename_model`, `remove_model`, `list_models`
- **Model elements:** `create_*`, `modify_*`, `remove_*`, and `list_*` for
  compartments, species, reactions, and parameters
- **Simulation:** `get_simulation_settings`, `configure_simulation`,
  `simulate_model` (optionally applying named `doses`/`variants` for the run)
- **Dosing:** `create_dose`, `modify_dose`, `list_doses`, `remove_dose`
  (repeat and schedule doses; bolus or zero-order infusion)
- **Variants:** `create_variant`, `modify_variant`, `list_variants`,
  `remove_variant` (named parameter/species/compartment overrides, e.g. knockouts)
- **Export:** `export_graph` (PNG plot of a simulation) and `export_csv`
  (simulation time-course as CSV written to a file at the required `path`);
  both accept the same `doses`, `variants`, and `species`
  arguments as `simulate_model`, so exports reflect that exact run
- **Literature and parts:** `pubmed_search`, `pubmed_summary`, `pubmed_article`,
  `igem_part`, `igem_search`, `igem_search_best`

---

## Project layout

```
core/        SimBiology session, per-model reads, and command builders
engine/      Singleton MATLAB engine wrapper and error types
tools/       MCP tool definitions and the shared registry
external/    PubMed and iGEM API wrappers
interfaces/  FastMCP server wiring
examples/    Runnable demos (e.g. demo_simulation.py)
tests/       Unit tests plus MATLAB/live integration tests
```

---

## Development

Run the hermetic test suite (no MATLAB or network required):

```powershell
$env:PYTHONPATH = (Get-Location).Path
.\.venv\Scripts\python.exe -m pytest -m "not matlab and not live"
```

Integration tests are opt-in:

- `matlab`-marked tests run automatically when the MATLAB Engine is importable.
- `live`-marked tests hit external APIs and run only with `--run-live`.

CI runs the hermetic subset on every push and pull request.
