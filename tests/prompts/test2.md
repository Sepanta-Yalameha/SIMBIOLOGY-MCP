Using the SimBiology MCP tools ONLY, build, simulate, and export a **genetic toggle
switch coupled to Lux quorum sensing** in *Escherichia coli*, in:

projects/toggle_quorum/

Execute every step with MCP tools. This is a determinism probe: the architecture is
fixed, and this prompt deliberately exercises the dosing and variant tools. Research
the numeric parameters; do not invent them.

## The system (build exactly this topology)
- **Toggle switch** (Gardner, Cantor & Collins, *Nature*, 2000): two genes, **LacI**
  and **TetR**, whose promoters are each Hill-repressed by the other's protein
  (LacI represses the TetR promoter; TetR represses the LacI promoter). Model mRNA
  and protein for both.
- **Reporter:** **GFP** transcribed from the TetR-repressed promoter, so GFP reports
  one stable state of the switch.
- **Quorum sensing:** **LuxI** synthesizes the signal **AHL**; **LuxR** binds AHL to
  form a **LuxR-AHL complex** (association/dissociation) that activates a pLux
  promoter driving extra **LacI**, coupling cell-density signaling into the toggle.
- Use reaction rate expressions for all regulation (no rules/events).

## Research (use the MCP tools; cite everything in your report)
- `pubmed_*`: Hill coefficients and repression thresholds for the LacI/TetR toggle;
  LuxI AHL synthesis rate, LuxR-AHL association/dissociation constants, AHL
  degradation; transcription/translation and degradation rates. Convert half-lives
  to rate constants (k = ln(2)/half-life).
- `igem_part`: choose registry parts for pLac, pTet, pLux, LuxR, LuxI, GFP, and the
  RBSs. Record each part ID.

## Dosing and scenarios (use the NEW MCP tools)
- **Dose:** with `create_dose`, add an **IPTG bolus** that sequesters free LacI (a
  repeat/bolus dose on the LacI species, or an inducer species that does so) large
  enough to flip the switch. Research a reasonable IPTG amount.
- **Variants:** with `create_variant`, define:
  - `qs_on`: LuxI at its researched synthesis value (baseline).
  - `qs_off`: LuxI knocked out (its synthesis/translation parameter set to 0).

## Simulate (deterministic ode15s, 1000 minutes) and compare
1. Baseline toggle, no IPTG.
2. Toggle + IPTG dose (expect the switch to flip).
3. `qs_on` vs `qs_off` variants (quorum sensing's effect on the resting state).

## Outputs
- Report steady-state GFP for each run and whether/when the switch flipped.
- `export_graph` of run 2 (the IPTG flip), labeled and captioned ->
  projects/toggle_quorum/iptg_flip.png
- `export_csv` comparing the `qs_on` run -> projects/toggle_quorum/qs.csv
- Save the project -> projects/toggle_quorum/model.sbproj

## Constraints
- Deterministic ODE only.
- Use only compartments, species, parameters, reactions, doses, variants, simulate,
  and export (no rules/events/observables/SBML).
- Every numeric parameter must trace to a PubMed citation or an iGEM part.
