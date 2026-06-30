Using SimBiology MCP tools, create and analyze a full synthetic biology system in:

projects/toggle_quorum_sensing/

Construct an Escherichia coli genetic toggle switch coupled with Lux quorum sensing.

MANDATORY TOOL USE:

- All model building, querying, simulation, analysis, validation, and export must be done using SimBiology MCP tools.
- Do NOT provide manual explanations of steps unless requested; execute via tools.

External data requirements:

- Query iGEM Registry via MCP for genetic parts (promoters, repressors, LuxI/LuxR system, reporters, degradation tags).
- Query PubMed via MCP for all kinetic parameters:
  transcription/translation rates, binding affinities, Hill coefficients, degradation rates, diffusion constants, GFP maturation, growth rates.
- Every parameter must include a traceable citation.

Model must include:

- LacI/TetR mutual repression toggle switch
- LuxI/LuxR quorum sensing system
- AHL production, diffusion, and degradation (intra + extracellular compartments)
- GFP reporter
- Cell growth and dilution
- Metabolic burden effects on expression
- Protein degradation tags
- Resource limitation effects

Validate model using MCP tools and auto-repair inconsistencies.

Run analyses via MCP:

- Deterministic simulation
- 100-run stochastic simulation ensemble
- Dose-response analysis (IPTG and AHL)
- Bistability analysis
- Local + global sensitivity analysis
- Parameter scans (promoter strength, degradation rates)
- Monte Carlo uncertainty analysis
- Steady-state analysis
- Flux/reaction rate analysis
- Comparison: quorum sensing ON vs OFF
- Comparison: metabolic burden ON vs OFF

Export everything into:
projects/toggle_quorum_sensing/
including:

- SimBiology project file
- SBML model
- MATLAB code
- CSV outputs
- All figures (plots, heatmaps, phase diagrams, network graphs)
- Full reproducible report with citations and modeling decisions
