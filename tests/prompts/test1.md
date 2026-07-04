Using the SimBiology MCP tools ONLY, build, simulate, and export the classic
**repressilator** synthetic oscillator in *Escherichia coli*, in:

projects/repressilator/

Execute every step with MCP tools (do not describe actions; perform them). This is
a determinism probe: the architecture below is fixed so every model builds the SAME
circuit, and the only freedom is the parameter values, which you must obtain by
research. Two correct attempts should produce the same trajectory.

## The system (build exactly this topology; do not substitute another design)
A three-node ring oscillator (Elowitz & Leibler, *Nature*, 2000): three repressor
genes wired in a cycle so each represses the next.
- Repressors: **LacI, TetR, and lambda CI**.
- Cyclic repression: LacI represses the TetR gene; TetR represses the CI gene;
  CI represses the LacI gene.
- For EACH of the three genes, model both **mRNA** and **protein**, with:
  - repressed transcription using a Hill term:
    transcription rate = alpha / (1 + (repressor_protein / K)^n) + leak
  - first-order translation (mRNA -> protein)
  - first-order degradation of mRNA and of protein
- Represent regulation only through reaction rate expressions (this MCP has no
  rules/events; do not use them).

## Research (you MUST use the MCP tools; do not invent unsourced numbers)
- Use `pubmed_search` / `pubmed_article` to obtain the repressilator kinetic
  parameters from the original Elowitz & Leibler 2000 paper (and, if needed, the
  standard follow-up parameterizations): maximal transcription rate (alpha), leak,
  translation rate, mRNA and protein half-lives, Hill coefficient n, and repression
  threshold K. Convert half-lives to rate constants with k = ln(2) / half-life.
- Use `igem_part` to select the registry BioBrick parts you are representing
  (e.g. the pLac / pTet / pCI promoters, an RBS, and the LacI / TetR / CI coding
  sequences). Record each part's registry ID.
- In your final report, list every parameter, its value, and its PubMed citation or
  iGEM part ID.

## Build (MCP tools)
- One compartment representing the E. coli cell.
- Six species: LacI_mRNA, TetR_mRNA, CI_mRNA, LacI, TetR, CI.
- Initial conditions (use EXACTLY, to make the run reproducible): LacI = 5, every
  other species = 0. (This small asymmetry starts the oscillation.)

## Simulate (deterministic)
- Solver ode15s, stop time 1000 (minutes).

## Outputs
- Report the **oscillation period** and the **peak amplitude** of each repressor
  protein.
- `export_graph` of the three repressor proteins vs time (labeled, captioned) ->
  projects/repressilator/repressilator.png
- `export_csv` of that same time-course -> projects/repressilator/repressilator.csv
- Save the project -> projects/repressilator/model.sbproj

## Constraints
- Deterministic ODE only (no stochastic solver).
- Use only compartments, species, parameters, reactions, simulate, and export.
- Every numeric parameter must trace to a PubMed citation or an iGEM part.
