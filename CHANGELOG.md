# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

* Multi-run time-series overlays for `export_graph` and `export_csv` via a new `runs` parameter. Each run is a `{label, variants, doses, species}` scenario; the graph overlays every run's line(s) with a legend, and the CSV aligns the runs onto one shared time grid (`output_points` samples) as a single time column plus one data column per run. Omitting `runs` keeps the existing single-run behaviour unchanged.

## [0.1.0] - 2026-07-19

### Added

* Initial public release of the SimBiology MCP Server.
* MCP tools for creating, modifying, simulating, exporting, and analysing SimBiology models, plus PubMed and iGEM lookups.
* `simbiology-mcp` CLI for starting the server and installing MATLAB Engine for Python from a local MATLAB installation.
* Interactive and scripted MCP configuration for Claude Code, Cursor, Codex, Windsurf, GitHub Copilot CLI, and Visual Studio Code/GitHub Copilot.
* Packaged `synthetic-biology-modelling` skill installer, including optional installation as part of `simbiology-mcp setup`.
* Project-owned `simbiology_mcp` Python package namespace.

[unreleased]: https://github.com/Sepanta-Yalameha/SIMBIOLOGY-MCP/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/Sepanta-Yalameha/SIMBIOLOGY-MCP/releases/tag/v0.1.0
