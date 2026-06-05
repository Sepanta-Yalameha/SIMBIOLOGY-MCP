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
- Python 3.10–3.12 (recommended: 3.11)
- Windows operating system
- MCP-compatible runtime environment (e.g., VSCode MCP client or agent framework)

---

## Installation

Run the setup script to configure the environment:

```powershell
.\setup_venv.ps1
