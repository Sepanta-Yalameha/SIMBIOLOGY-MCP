Using the SimBiology MCP tools ONLY, build, simulate, and export a one-compartment
**pharmacokinetic (PK) model** of a renally-cleared drug, and study dosing regimens
and patient scenarios, in:

projects/pk_dosing/

Execute every step with MCP tools. This prompt is the focused test of the newer
capabilities: repeat and schedule **doses**, scenario **variants**, and
**reproducible export**. The structure is fixed; research the PK numbers rather than
inventing them.

## The system (build exactly this)
- One compartment `central`, whose capacity is the drug's volume of distribution.
- Species `Drug` in `central`, with first-order elimination: reaction `Drug -> null`
  with rate expression `ke * Drug`.
- Parameter `ke` = the elimination rate constant.

## Research (use the MCP literature tools; cite everything)
- Model **gentamicin** (a renally-cleared aminoglycoside). Use `pubmed_search` /
  `pubmed_article` to find, in adults: its **elimination half-life with normal renal
  function**, its **elimination half-life in renal impairment**, and its **volume of
  distribution**. Derive `ke = ln(2) / half_life` for the normal and impaired cases.
- Research a **typical IV dose amount** (mg) and dosing interval for gentamicin.
- Report every value with its PubMed citation. (No iGEM parts are needed here.)

## Dosing (use `create_dose`)
- Repeat IV bolus `q8h`: your researched dose amount, start time 0, interval 8 hours,
  several doses (bolus, rate 0), targeting `Drug`.
- Schedule dose `loading_then_maint`: a larger loading dose at t = 0 followed by
  maintenance doses at researched times, using the schedule-dose form (times +
  amounts).

## Scenarios (use `create_variant`)
- `renal_impairment`: `ke` set to the impaired-renal-function value you researched.
- `anuria`: `ke` set to 0 (no elimination at all).

## Simulate (deterministic ode15s, 48 hours), applying doses/variants BY NAME
1. `q8h`, normal renal function (no variant).
2. `q8h` under `renal_impairment`.
3. `q8h` under `anuria`.
4. `loading_then_maint`, normal renal function.

## Outputs (must reflect the exact run: this checks export reproducibility)
- Report Cmax and the t = 48 h trough for each of the four runs. Confirm that
  `renal_impairment` accumulates more drug than normal, and that `anuria` rises
  monotonically after each dose.
- `export_graph` of run 2 (q8h + renal_impairment) ->
  projects/pk_dosing/q8h_renal.png
- `export_csv` of run 2 -> projects/pk_dosing/q8h_renal.csv, and confirm its `Drug`
  column equals the `simulate_model` result for run 2 at the same time points.
- Save the project -> projects/pk_dosing/model.sbproj

## Constraints
- Deterministic ODE only.
- Use only compartments, species, parameters, reactions, doses, variants, simulate,
  and export.
- Every PK number must be sourced from PubMed.
