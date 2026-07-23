# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

* `pubmed_fulltext` tool: fetches section-labeled open-access full text for a PubMed article from PubMed Central (BioC API), where Methods, Results, and Tables carry kinetic constants. Falls back to the PubMed abstract with `full_text_available` False when the paper is not open access.
* `sabio_search` and `sabio_entry` tools: look up measured enzyme kinetics (Km, kcat, Vmax, Ki) from SABIO-RK using a fielded query (Organism, Substrate, ECNumber, Parametertype) or an entry id. Each parameter carries both the as-reported unit and an SI-normalized value, and the source publication cross-references PubMed.

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
