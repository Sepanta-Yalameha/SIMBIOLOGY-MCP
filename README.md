# SimBiology MCP Server

[![PyPI](https://img.shields.io/pypi/v/simbiology-mcp?logo=pypi\&logoColor=white)](https://pypi.org/project/simbiology-mcp/)
[![Python](https://img.shields.io/pypi/pyversions/simbiology-mcp?logo=python\&logoColor=white)](https://pypi.org/project/simbiology-mcp/)
[![Tests](https://github.com/Sepanta-Yalameha/SIMBIOLOGY-MCP/actions/workflows/test.yml/badge.svg?branch=main)](https://github.com/Sepanta-Yalameha/SIMBIOLOGY-MCP/actions/workflows/test.yml?query=branch%3Amain)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![MATLAB](https://img.shields.io/badge/MATLAB-R2024a%2B-orange)](https://www.mathworks.com/products/matlab.html)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-blue)](#requirements)

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

Choose one way to install the Python package, then complete the common setup steps below.

### 1. Manual repo checkout

Use this when you want the full source tree locally, including the repo skill files and tests.

```shell
git clone https://github.com/Sepanta-Yalameha/SIMBIOLOGY-MCP.git
cd SIMBIOLOGY-MCP
python -m venv .venv
```

Activate the virtual environment:

```powershell
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
```

```shell
# macOS or Linux
source .venv/bin/activate
```

```shell
python -m pip install -e .
```

### 2. Recommended: `uv tool install`

Use this when you want a cleaner install without cloning the repo.

```powershell
uv tool install simbiology-mcp
```

### 3. Plain `pip`

Use this if you do not want `uv tool install`.

```powershell
python -m pip install simbiology-mcp
```

## Complete the setup

The easiest option is the interactive setup. It installs the MATLAB Engine, configures an MCP client, and offers to install the matching skill:

```powershell
simbiology-mcp setup
```

For a fully interactive setup, follow the prompts to choose your MATLAB installation, client, configuration scope, and skill destination.

For headless or engine-only setup, install the MATLAB Engine for Python from your local MATLAB installation:

```powershell
simbiology-mcp setup --skip-configure
```

If multiple MATLAB installations are found, select one interactively or pass an index:

```powershell
simbiology-mcp setup --matlab-index 0 --skip-configure
```

Configure an MCP client:

```powershell
simbiology-mcp configure --client cursor
simbiology-mcp configure --client codex --project
simbiology-mcp configure --list-clients
```

The configuration helper supports Claude Code, Cursor, Codex, Windsurf, GitHub Copilot CLI, and Visual Studio Code/GitHub Copilot. The user scope is the default; use `--project` for project-local configuration. Existing matching entries are left unchanged; use `--force` to replace a different existing entry.

Install the synthetic biology modelling skill separately:

```powershell
simbiology-mcp get-skill --client codex
```

Use `--client`, `--project`, `--user`, or `--install-path` to choose a destination directly. Run `simbiology-mcp get-skill` without flags for the interactive picker.

Add `--no-skill` to omit the skill installation.

---

## Requirements

- MATLAB R2024a or later
- SimBiology Toolbox installed
- Python 3.12 or later
- A MATLAB-supported Windows, macOS, or Linux environment
- An MCP-compatible client; the configuration helper supports Claude Code, Cursor, Codex, Windsurf, GitHub Copilot CLI, and Visual Studio Code/GitHub Copilot

---

## Usage

Once setup has configured the MCP server for your chosen agent, launch or restart that agent's client session. The client starts the server automatically when it connects to it; you do not need to run `start` manually.

### Manual configuration and server start

Use manual configuration only when your client is not supported by `configure`:

Point your MCP client at the installed server executable. Use the absolute path so the client does not depend on your shell's `PATH`:

```json
{
  "mcpServers": {
    "simbiology": {
      "command": "C:/absolute/path/to/simbiology-mcp.exe",
      "args": ["start"]
    }
  }
}
```

Alternatively, run the server directly from an activated repository environment:

```powershell
python -m simbiology_mcp start
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
| `export_graph`, `export_csv` | Export the same run used by `simulate_model` to PNG or CSV, or overlay several runs on one graph/CSV. | Optional path plus optional `species`, `doses`, and `variants`, plus an optional `runs` list (one `{label, variants, doses, species}` per overlaid scenario). | File metadata or inline CSV text. |
| `list_series`, `steady_state`, `series_min`, `series_max` | Analyze exported CSV data without rerunning MATLAB. | CSV path and target series name. | Series names or computed values. |
| `pubmed_search`, `pubmed_summary`, `pubmed_article` | Pull literature context from PubMed. | Query, PubMed ID, and summary options. | Search hits, article details, or summaries. |
| `igem_part`, `igem_search`, `igem_search_best` | Look up parts from the iGEM registry. | Exact identifier or free-text query. | Part records or ranked matches. |

---

## Project layout

```text
simbiology_mcp/
├── core/        SimBiology session, per-model reads, and command builders
├── engine/      Singleton MATLAB engine wrapper and error types
├── tools/       MCP tool definitions and the shared registry
├── external/    PubMed and iGEM API wrappers
├── interfaces/  FastMCP server wiring
├── scripts/     CLI helpers like setup, configure, and get-skill
└── skills/      Packaged skill markdown
examples/        Runnable demos (e.g. demo_simulation.py)
tests/           Unit tests plus MATLAB/live integration tests
```

## Authors

- [Yojith Sai Biradavolu](https://github.com/yojith)
- [Sepanta Yalameha](https://github.com/Sepanta-Yalameha)

Contributions, issues, and feature requests are welcome through the project’s [GitHub repository](https://github.com/Sepanta-Yalameha/SIMBIOLOGY-MCP).

---

## Development

Run the hermetic test suite (no MATLAB or network required):

```powershell
py -m pytest -m "not matlab and not live"
```

`matlab` tests require a working MATLAB Engine install. `live` tests hit external APIs and run only with `--run-live`.
