# SimBiology MCP Server

## Overview

The SimBiology MCP Server is a Model Context Protocol (MCP) interface for MATLAB SimBiology, enabling programmatic control of biological modeling and simulation workflows from AI agents and external tools.

It bridges large language model systems with MATLAB's SimBiology toolbox through the MATLAB Engine for Python, allowing automated creation, modification, and execution of computational biology models.

---

## Purpose

SimBiology is a powerful environment for modeling biochemical and pharmacokinetic systems, but it is primarily MATLAB-driven and interactive.

This MCP server provides a structured programmatic layer that:

- Exposes SimBiology functionality as MCP tools
- Enables automated model construction and simulation
- Supports agent-driven workflows for systems biology
- Removes the need for manual MATLAB interaction
- Supports workflows such as building PK/PD models, modifying reactions and parameters, simulating time courses, exporting results, and pulling supporting context from PubMed and iGEM

---

## Installation

Three installation paths are supported.

### 1. Manual repo checkout

Use this when you want the full source tree locally, including the repo skill files and tests.

```powershell
git clone https://github.com/Sepanta-Yalameha/SIMBIOLOGY-MCP.git
cd SIMBIOLOGY-MCP
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
simbiology-mcp setup
```

Then point your MCP client at the repo entry point:

```json
{
  "mcpServers": {
    "simbiology": {
      "command": "C:/path/to/SIMBIOLOGY-MCP/.venv/Scripts/python.exe",
      "args": ["C:/path/to/SIMBIOLOGY-MCP/main.py"]
    }
  }
}
```

### 2. Recommended: `uv tool install`

Use this when you want a cleaner install without cloning the repo.

```powershell
uv tool install simbiology-mcp
simbiology-mcp setup
```

Then point your MCP client at the installed `simbiology-mcp` command with the `start` subcommand. To get the packaged skill guidance, run:

```powershell
simbiology-mcp get-skill
```

That helper prints the packaged `SKILL.md` to the terminal by default. To copy it to a specific location instead, pass an explicit destination:

```powershell
simbiology-mcp get-skill --install-path C:\path\to\SKILL.md
```

### 3. Plain `pip`

Use this if you do not want `uv tool install`.

```powershell
python -m pip install simbiology-mcp
simbiology-mcp setup
simbiology-mcp get-skill
```

---

## Requirements

- MATLAB R2024a or later
- SimBiology Toolbox installed
- Python 3.12 or later
- Windows operating system
- MCP-compatible runtime environment (e.g., VSCode MCP client or agent framework)

---

## Usage

Start the server over stdio, either through the repo entry point or the installed command:

```powershell
# from the repo
.\.venv\Scripts\python.exe .\main.py

# or, after installation
simbiology-mcp start
```

### Wiring into an MCP client

Point your MCP client at the server command. A typical stdio configuration for an installed command:

```json
{
  "mcpServers": {
    "simbiology": {
      "command": "simbiology-mcp",
      "args": ["start"]
    }
  }
}
```

The MATLAB engine starts lazily on the first tool call that needs it, so client startup stays fast.

### External API keys

PubMed works without a key but is rate-limited. To raise the limit, copy `.env.example` to `.env` and set `NCBI_API_KEY`.

---

## Tools

The server exposes the following MCP tools:

| Tool name | Description | Inputs | Outputs |
| --- | --- | --- | --- |
| `load_project`, `create_project`, `save_project` | Load, create, and persist SimBiology projects. | Project path, model name, save target. | Confirmation plus project/model metadata. |
| `create_model`, `rename_model`, `remove_model`, `list_models` | Manage models inside the loaded project. | Model name or rename target. | Confirmation or model name lists. |
| `create_compartment`, `modify_compartment`, `remove_compartment`, `list_compartments` | Manage compartments. | Names plus compartment properties such as capacity and units. | Confirmation or compartment data. |
| `create_species`, `modify_species`, `remove_species`, `list_species` | Manage species. | Names plus species properties such as initial amount and units. | Confirmation or species data. |
| `create_reaction`, `modify_reaction`, `remove_reaction`, `list_reactions` | Manage reactions and rate expressions. | Reactants, products, reversibility, rate law fields. | Confirmation or reaction data. |
| `create_parameter`, `modify_parameter`, `remove_parameter`, `list_parameters` | Manage model parameters. | Names, values, units, and scope. | Confirmation or parameter data. |
| `get_simulation_settings`, `configure_simulation`, `simulate_model` | Inspect, configure, and run simulations. | Solver/settings fields, optional `species`, `doses`, `variants`, and output limits. | Current settings or simulation result rows. |
| `create_dose`, `modify_dose`, `remove_dose`, `list_doses` | Manage repeat and schedule doses. | Dose type, target, timing, amount/rate fields. Dose amounts use amount/mass units; dose rates use amount/time or mass/time units. | Confirmation or dose data. |
| `create_variant`, `modify_variant`, `remove_variant`, `list_variants` | Manage named model overrides. | Variant name and full content entries. | Confirmation or variant data. |
| `export_graph`, `export_csv` | Export the same run used by `simulate_model` to PNG or CSV. | Optional path plus optional `species`, `doses`, and `variants`. | File metadata or inline CSV text. |
| `list_series`, `steady_state`, `series_min`, `series_max` | Analyze exported CSV data without rerunning MATLAB. | CSV path and target series name. | Series names or computed values. |
| `pubmed_search`, `pubmed_summary`, `pubmed_article` | Pull literature context from PubMed. | Query, PubMed ID, and summary options. | Search hits, article details, or summaries. |
| `igem_part`, `igem_search`, `igem_search_best` | Look up parts from the iGEM registry. | Exact identifier or free-text query. | Part records or ranked matches. |

---

## Project layout

```text
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
py -m pytest -m "not matlab and not live"
```

`matlab` tests require a working MATLAB Engine install. `live` tests hit external APIs and run only with `--run-live`.
