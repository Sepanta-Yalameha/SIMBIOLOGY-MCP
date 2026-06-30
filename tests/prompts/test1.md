Using the SimBiology MCP tools, create a complete SimBiology project in the directory:

projects/repressilator_basic/

Build a classical repressilator synthetic gene circuit in Escherichia coli.

Requirements:

- Use SimBiology MCP tools for ALL model construction, editing, simulation, and export steps (do not describe actions—execute them via tools).
- Query the iGEM Registry via available MCP integrations to select realistic promoters, repressors (e.g., LacI, TetR, CI), RBSs, terminators, GFP reporter, and degradation tags.
- Query PubMed via MCP tools for experimentally measured kinetic parameters (transcription/translation rates, degradation constants, Hill coefficients, protein half-lives).
- Every parameter must include a citation from PubMed or equivalent literature source.
- Build the model programmatically using SimBiology MCP:
  - compartments
  - species
  - parameters
  - reactions
  - rules
  - events
  - observables
  - units consistency
- Validate model structure using MCP tools and automatically fix any errors.

Simulations (run via MCP tools):

- Deterministic simulation (0–1000 min)
- Stochastic simulation (50 replicates)
- Parameter scan over promoter strengths
- Sensitivity analysis
- Dose-response analysis
- Steady-state analysis

Outputs (export using MCP tools into projects folder):

- Time-course plots
- Oscillation period analysis
- Sensitivity heatmaps
- Network diagram of circuit
- Summary tables of species/parameters
- CSV datasets of simulation results
- SBML export
- MATLAB SimBiology project export
- Full reproducible report with citations

Ensure everything is saved under:
projects/repressilator_basic/
