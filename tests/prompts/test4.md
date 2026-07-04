Using the SimBiology MCP tools ONLY, build, simulate, and export a one-compartment
pharmacokinetic (PK) model with dosing and variant scenarios, in:

projects/pk_dosing_variant/

PURPOSE: This is a determinism check. Every quantity is specified exactly, so any
capable model driving the MCP correctly must produce the SAME numeric results. Do
NOT query iGEM or PubMed, and do NOT invent or "improve" any value — use exactly the
numbers below. Use SimBiology MCP tools for every step (do not describe actions;
execute them via tools).

BUILDABLE-TODAY ONLY: Use only these capabilities — compartments, species,
parameters, reactions, simulation settings, doses, variants, simulate, and export.
Do NOT use rules, events, observables, SBML export, MATLAB code export, stochastic
solvers, or sensitivity analysis. This model is deterministic by construction.

MODEL (build with MCP tools):
- Compartment: `central`, capacity 1.0
- Species: `Drug` in `central`, initial amount 0
- Parameter: `ke`, value 0.35   (first-order elimination rate, 1/hour)
- Reaction: name `elimination`, equation `Drug -> null`, rate expression `ke*Drug`
- Simulation settings: solver `ode15s`, stop time `48`

DOSES (create with MCP tools, targeting species `Drug`):
- Repeat dose `q8h`: amount 100, start time 0, interval 8, repeat_count 5
  (i.e. 6 bolus doses total), rate 0 (bolus).
- Schedule dose `loading`: times [0, 12, 24], amounts [200, 100, 100].

VARIANTS (create with MCP tools):
- `renal_impairment`: set parameter `ke` to 0.15.
- `no_elimination`: set parameter `ke` to 0 (knockout of elimination).

SIMULATIONS (run via simulate_model, applying doses/variants BY NAME):
1. Baseline: dose `q8h`, no variant.
2. Impaired: dose `q8h` under variant `renal_impairment`.
3. Knockout: dose `q8h` under variant `no_elimination`.
4. Loading:  dose `loading`, no variant.

EXPORTS (must reflect the exact simulation, not a bare re-run):
- export_graph of simulation (2) [q8h + renal_impairment] to
  projects/pk_dosing_variant/q8h_renal.png
- export_csv of simulation (2); save the returned CSV text to
  projects/pk_dosing_variant/q8h_renal.csv

Also save the SimBiology project to projects/pk_dosing_variant/model.sbproj.

REPORT (concise, so results can be compared across models):
- For each of the 4 simulations: peak `Drug` amount (Cmax) and the time it occurs.
- Confirm sim (2) reaches a higher final `Drug` amount at t=48 than sim (1)
  (slower elimination accumulates more drug).
- Confirm sim (3) never decreases after a dose (no elimination -> monotonic
  accumulation up to 600 at t>=40).
- Confirm the exported CSV's `Drug` column equals the simulate_model result for
  sim (2) at the same time points.
