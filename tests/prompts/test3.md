Using SimBiology MCP tools ONLY, design, build, validate, simulate, and export a full multi-scale synthetic biology digital twin in:

projects/ecoli_digital_twin_full/

You are building a publication-quality computational model of engineered Escherichia coli used for recombinant protein production with quorum sensing coordination, metabolic burden, and full cellular resource allocation.

STRICT REQUIREMENTS:

- All actions must be executed using SimBiology MCP tools (model creation, editing, simulation, analysis, validation, export).
- Query iGEM Registry via MCP for all genetic parts and justify selection based on retrieved data.
- Query PubMed via MCP for ALL parameters:
  kinetic rates, transcription/translation rates, ribosome allocation, plasmid copy number effects, metabolic flux constraints, ATP usage, degradation rates, diffusion constants, enzyme kinetics, growth models.
- No parameter may be assumed without a citation.

MODEL MUST INCLUDE:

- Gene regulation networks
- Transcription and translation
- RNA and protein degradation
- Protein folding (lumped or explicit)
- Recombinant protein production pathway
- Plasmid replication and copy number dynamics
- Cell growth, division, and dilution
- Resource allocation (ribosomes, ATP, nutrients)
- Metabolic burden feedback on expression
- Glucose uptake and biomass formation
- Quorum sensing (Lux system or equivalent)
- Intra/extracellular transport
- Multi-compartment structure
- Events, rules, variants, doses, observables
- Full unit consistency enforcement
- Automatic error detection and self-correction via MCP tools

ANALYSES (must be executed via MCP tools):

1. Deterministic simulation (0–2000 min)
2. Gillespie stochastic simulation (≥500 replicates)
3. Population heterogeneity analysis
4. Local sensitivity analysis
5. Global sensitivity analysis
6. Sobol sensitivity analysis (if available)
7. Monte Carlo uncertainty analysis
8. Latin Hypercube sampling
9. Multi-parameter scans (≥20 parameters)
10. Steady-state analysis
11. Flux balance-style reaction rate analysis
12. Bifurcation-like behavior detection
13. Robustness analysis under perturbations
14. Knockout simulations (gene deletions)
15. Promoter substitution studies
16. Metabolic burden stress tests
17. Resource competition stress tests
18. Parameter identifiability checks

AUTO-RECOVERY:

- If simulations fail, are stiff, unstable, or inconsistent, automatically diagnose and fix using MCP tools and rerun.

OUTPUTS (export into project folder):
projects/ecoli_digital_twin_full/

- Complete SimBiology project
- SBML export
- MATLAB code export
- Full dataset exports (CSV)
- All figures (time series, phase plots, heatmaps, histograms, violin plots, sensitivity maps, network diagrams)
- Parameter tables and reaction tables
- Full reproducible report with:
  - all modeling decisions
  - all PubMed/iGEM citations
  - all validation steps
  - interpretation of biological behavior
  - limitations and future improvements
  - experimental validation proposals
