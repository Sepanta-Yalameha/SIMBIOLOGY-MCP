---
name: synthetic-biology-modelling
description: Use when building, modifying, simulating, exporting, or analysing synthetic biology and genetic-circuit models through the SimBiology MCP.
---

# Synthetic Biology Modelling

Use this skill when the user wants to model or simulate a genetic circuit, engineered biological system, biosensor, or related synthetic biology network through the SimBiology MCP.

The SimBiology MCP provides tools to:

- create and modify SimBiology projects and models
- create species, compartments, reactions, parameters, doses, and variants
- simulate models and export results
- analyze exported CSV outputs
- search PubMed and the iGEM Registry for supporting biological information

When the SimBiology MCP tools are available, use them as the primary interface. Avoid issuing raw MATLAB commands or using Python wrappers around MATLAB commands on your own unless the MCP tool surface is missing a capability that is strictly necessary for the task.

## Workflow

Follow this order unless the user explicitly needs something different:

1. Understand the biology and plan the circuit before editing the model.
2. Identify all species, reactions, parameters, compartments, and assumptions.
3. Create or load the `.sbproj` and select the correct model.
4. Build the model completely.
5. Configure simulation only as needed.
6. Run the simulation.
7. Export CSV and PNG results.
8. Analyze results with MCP analysis tools when possible.
9. Save the project after the work is complete.

**Always use the SimBiology MCP tools when they are available. Do not bypass them with raw MATLAB commands, handwritten MATLAB snippets, or Python wrappers around MATLAB unless the MCP tool surface is genuinely missing a required capability.**

## Modeling Terms

- **Species**: Any quantity that changes over time, such as proteins, mRNA, complexes, metabolites, or input molecules.
- **Reactions**: Creation, loss, binding, conversion, catalysis, transcription, translation, or other dynamic processes involving species.
- **Parameters**: Constants used in rate laws or initialization, such as rate constants, Hill constants, Michaelis-Menten constants, temperature constants, and volume terms.
- **Compartment**: The physical region containing the species, usually a cell or reactor volume.

## Model Creation

Plan the circuit before creating anything. Identify:

- all species
- all reactions
- all parameters and constants
- all compartments
- all external inputs
- all outputs the user cares about

Then:

- If this is a new project, create a new `.sbproj`, a model, and a compartment.
- If this is an existing project, load the `.sbproj` and select the correct model.
- When creating a compartment, always provide a capacity. In most synthetic biology cases this is the cell volume.
- Every species must have units.
- Every parameter must have a numerical value and units.
- Every reaction rate law must be dimensionally consistent.

## Completeness Rules

Build the model completely before simulating.

- If the system produces a protein, include transcription to its mRNA, translation from mRNA to protein, mRNA loss, and protein loss.
- Treat enzymes like any other expressed protein unless the prompt explicitly says they are externally supplied or already present. If the model contains an enzyme species, usually also create its mRNA plus the transcription, translation, mRNA-loss, and protein-loss reactions that produce and clear it.
- All internal species should generally have a loss or degradation reaction.
- A pure external input signal may be exempt from degradation if that is the intended assumption.
- Do not create unused parameters unless they have a clear purpose in the model.
- Validate constants with iGEM, PubMed, or other scientific sources when possible.

## Simulation

Once the model is complete:

- configure stop time
- leave the default differential equation solver unless the user requests something else
- use doses or variants when the user wants time-dependent or scenario-dependent changes
- run the simulation and inspect the time course of the species

### Doses

Use a **dose** when something changes during the simulation at a defined time or schedule.

Examples:

- inject or add an input molecule at a certain time
- repeatedly add a species
- apply a schedule of concentration changes

Typical dose information includes:

- target species
- amount
- time
- rate
- repeat/schedule settings

### Variants

Use a **variant** for named model overrides that define a scenario without permanently changing the base model structure.

Variants are useful for:

- knockouts
- overexpression scenarios
- changing parameter values for alternative experimental conditions
- changing species initial amounts
- changing compartment properties for a scenario

In this MCP, variant content is a list of entries with:

- `type`
- `name`
- `property`
- `value`

Practical guidance:

- create variants before simulation when the user wants alternate model conditions
- prefer variants over repeatedly mutating the base model for scenario testing
- keep each variant internally coherent and clearly named
- remember that modifying a variant replaces its full content, so provide the complete intended variant definition

## Export and Analysis

After simulation:

- export the results to CSV
- export the graph to PNG
- use the analysis MCP tools whenever possible instead of manually scanning large outputs
- ground kinetic constants (Km, kcat, Vmax, Ki) in measured data via `sabio_search`, and pull open-access paper full text (Methods, Results, Tables) via `pubmed_fulltext` when the abstract alone is not enough
- save the project after the work is complete

Use analysis tools first when available because they reduce token waste and keep analysis reproducible.

## Common Reaction Types

Use these patterns whenever they match the biology. If the biology requires something else, identify the correct reaction and rate law explicitly.

| Reaction type | Equation pattern | Rate pattern | Parameters needed | Notes |
| --- | --- | --- | --- | --- |
| Baseline transcription | `null -> mRNA_A` with reaction name like `A_trsc` | `k_trsc` | `k_trsc` | Use when a promoter is unregulated and the transcript is created from an assumed source. |
| Baseline translation | `mRNA_A -> mRNA_A + A` with reaction name like `A_trsl` | `k_trsl*mRNA_A` | `k_trsl` | mRNA is not consumed during translation, so it appears on both sides. |
| mRNA loss | `mRNA_A -> null` with reaction name like `mRNA_A_loss` | `k_mRNA_loss*mRNA_A` | `k_mRNA_loss` | This is often modeled as a shared pattern across mRNA species unless the problem says otherwise. |
| Protein loss | `A -> null` with reaction name like `A_loss` | `k_pro_loss*A` | `k_pro_loss` | Use for ordinary protein degradation/loss. |
| Positive regulator on promoter | `null -> mRNA_E` with reaction name like `E_trsc` | `k_trsc_E*((R/K_R)/(1+R/K_R))` | `k_trsc_E`, `K_R`, species `R` | Use when a promoter is positively regulated by a complex or regulator. |
| Negative regulator on promoter | `null -> mRNA_E` with reaction name like `E_trsc` | `k_trsc_E*(1/(1+R/K_R))` | `k_trsc_E`, `K_R`, species `R` | Use when a promoter is negatively regulated or repressed by a regulator. |
| pH-regulated promoter | `null -> mRNA_E` with reaction name like `E_trsc` | use the positive or negative regulator form with `[H+]` as the regulator | `k_trsc_E`, `K_H`, effective regulator term for `[H+]` | Frame this as **H+-activated** or **H+-repressed** promoter regulation. Lower pH means higher `[H+]`; higher pH means lower `[H+]`. |
| Toe-hold-switch-regulated translation | `mRNA_B -> mRNA_B + B` with reaction name like `B_trsl` | `rate = k_trsl_B*(X/(K_X+X))` | `k_trsl_B`, `K_X`, species `X` | Use when the coding sequence / translation step is positively regulated by a biomarker or toe-hold switch. The biomarker is a regulator, not a reactant: do not multiply the activation term by `mRNA_B` again. |
| Negative regulator on translation | `mRNA_B -> mRNA_B + B` with reaction name like `B_trsl` | `k_trsl_B*(1/(1+R/K_R))` | `k_trsl_B`, `K_R`, species `R` | Use when a coding sequence or translation step is negatively regulated. |
| Heat-activated temperature-dependent transcription | `null -> mRNA_C` with reaction name like `C_trsc` | `k_trsc_C*(1/(1+exp(-(Temp-Temp_half)/sigma)))` | `k_trsc_C`, `Temp`, `Temp_half`, `sigma` | Use when higher temperature increases promoter activity. `Temp` is typically in Kelvin. |
| Cold-activated temperature-dependent transcription | `null -> mRNA_C` with reaction name like `C_trsc` | `k_trsc_C*(1/(1+exp((Temp-Temp_half)/sigma)))` | `k_trsc_C`, `Temp`, `Temp_half`, `sigma` | Use when lower temperature increases promoter activity. This is the inverse orientation of the heat-activated logistic form. |
| Michaelis-Menten catalysis | `B + C -> B + D` with reaction name like `Catalysis` | `kcat*B*C/(Km+C)` | `kcat`, `Km` | The catalyst is not consumed, so it appears on both sides. |
| Reversible complexation | `A + D <-> AD` with reaction name like `Complexation` | `ka*A*D - kd*AD` | `ka`, `kd` | Use for reversible binding / complex formation. Model this as one reversible reaction with a net rate of forward minus reverse, not as two separate reactions unless the prompt explicitly requires that structure. |
| General Hill-style regulation | Varies by system | use the problem-specific activation or repression expression | regulator constant(s), Hill coefficient if needed, base rate constant | Use when the system statement explicitly describes promoter or coding-sequence regulation. |

Use the correct rate law for the biology. Do not force a reaction into a mass-action interpretation if the biology requires a custom rate expression. In this MCP, reaction creation supports a reaction equation plus a `rate` expression; it does not expose a separate kinetic-law selector. In practice, that means:

- use plain mass-action-style rate expressions when the biology is truly mass action
- use custom rate expressions when the biology calls for Hill regulation, Michaelis-Menten behavior, temperature dependence, or other non-mass-action behavior
- for reversible reactions, prefer one `<->` reaction with a single net rate expression such as `k_a*Protein_A*Protein_D - k_d*AD` instead of splitting it into separate forward and reverse reactions, unless the prompt explicitly requires separate reactions
- if a species acts as a catalyst or enzyme in a reaction, include it on both sides of the reaction equation so it cancels out instead of being consumed
- for biomarker-gated or other regulator-gated transcription/translation, keep the regulator in the rate law and keep the expression species on its normal production/consumption pattern; do not turn the regulator into an extra reactant or multiply the activation term by the expression species again
- if a reaction rate looks dimensionally awkward, re-check the topology and intended biology from the ground up before patching the equation; do not “repair” units by inventing extra reactants, factors, or helper variables unless the biology really requires them
- do not treat an "unknown reaction" style warning as a reason to simplify the biology incorrectly; keep the accurate rate expression

## Helpful Equations

Use these equation patterns directly when they match the biology described by the user.

| Pattern | Equation |
| --- | --- |
| Baseline transcription | `rate = k_trsc` |
| Baseline translation | `rate = k_trsl*mRNA_A` |
| mRNA loss | `rate = k_mRNA_loss*mRNA_A` |
| Protein loss | `rate = k_pro_loss*A` |
| Positive regulation / Hill-style activation | `rate = k*((R/K_R)/(1+R/K_R))` |
| Negative regulation / Hill-style repression | `rate = k*(1/(1+R/K_R))` |
| pH-regulated promoter | `rate = k*(( [H+]/K_H )/(1+[H+]/K_H))` for H+-activated regulation, or `rate = k*(1/(1+[H+]/K_H))` for H+-repressed regulation |
| Toe-hold-switch-regulated translation | `rate = k_trsl_B*(X/(K_X+X))` |
| Negative regulation of translation | `rate = k_trsl_B*(1/(1+R/K_R))` |
| Negative regulation of transcription | `rate = k_trsc_E*(1/(1+R/K_R))` |
| Heat-activated temperature-sensitive promoter | `rate = k_trsc_C*(1/(1+exp(-(Temp-Temp_half)/sigma)))` |
| Cold-activated temperature-sensitive promoter | `rate = k_trsc_C*(1/(1+exp((Temp-Temp_half)/sigma)))` |
| Michaelis-Menten catalysis | `rate = kcat*B*C/(Km+C)` |
| Reversible complexation | `rate = ka*A*D - kd*AD` |
| Event-style step change | trigger: `time >= 100`, action: `X = 100e-9` |

Notes:

- If a promoter is being regulated, the regulation typically affects **transcription**.
- If a coding sequence or translation-related element such as a toe-hold switch is being regulated, the regulation typically affects **translation**.
- If a protein is labeled or described as an enzyme, do not jump straight to the catalytic reaction unless the prompt explicitly says the enzyme is externally supplied; usually you must also model how that enzyme is expressed.
- Catalysts are conserved across the elementary reaction they catalyze. Write them on both sides, for example `E + S -> E + P`, unless the biology explicitly says the catalyst is consumed or modified.
- pH-style regulation should be framed in terms of `[H+]`, not informal “low pH vs high pH” language alone. If the system activates as pH drops, that means it is **H+-activated** because `[H+]` increases as pH decreases.
- Heat-dependent and cold-dependent regulation use opposite logistic orientations; choose the sign that matches whether activity should increase with higher temperature or lower temperature.

## Units Summary
There are several unit types in SimBiology. Use the correct units for each species, parameter, dose, and reaction, and keep every rate law dimensionally consistent.

Rule of thumb:

- Use **amount** units for discrete counts or total substance, such as `mole`, `mmole`, or `umole`.
- Use **concentration** units for species in a compartment, such as `mole/liter`, `molarity`, or `uM`.
- Use **volume** units for compartments, such as `liter`, `m^3`, or `ml`.
- Use **time** units for simulation time and kinetic time constants, such as `second`, `minute`, or `hour`.
- Use **rate** units that match the quantity being changed per time, such as `mole/second`, `molarity/hour`, or `liter/second`.
- Use **dimensionless** units for pure ratios, probabilities, fractions, and Hill-like terms.

Common SimBiology patterns:

| Item | Typical unit family | Examples | Dimension check |
| --- | --- | --- | --- |
| Species initial amount | Amount or concentration | `mole`, `molarity`, `uM` | Match the species representation used in the compartment. |
| Compartment capacity | Volume | `liter`, `ml` | Must be a volume-like unit. |
| Parameter value | Depends on the formula | `1/second`, `liter/(mole*second)`, `dimensionless` | Units must make the full rate law balance. |
| Reaction rate | Quantity per time | `mole/second`, `molarity/minute` | The left and right sides of the reaction must imply the same overall units. |
| Dose amount | Amount or mass | `mole`, `milligram` | Do not use concentration units for a dose amount. |
| Dose rate | Amount/time or mass/time | `mole/second`, `milligram/hour` | Do not use concentration-based units for a dose rate. |

If a reaction uses concentration species in a volume compartment, check that the kinetic law converts cleanly between amount and concentration. If the rate looks wrong, fix the reaction topology or parameter dimensions rather than forcing units to fit.

## Tool Summary

The MCP exposes the following tool groups:

| Tool name | Description | Inputs | Outputs |
| --- | --- | --- | --- |
| `load_project`, `create_project`, `save_project` | Load, create, and persist SimBiology projects. | Project path, model name, save target. | Confirmation plus project/model metadata. |
| `create_model`, `rename_model`, `remove_model`, `list_models` | Manage models inside the loaded project. | Model name or rename target. | Confirmation or model name lists. |
| `create_compartment`, `modify_compartment`, `remove_compartment`, `list_compartments` | Manage compartments. | Names plus compartment properties such as capacity and units. | Confirmation or compartment data. |
| `create_species`, `modify_species`, `remove_species`, `list_species` | Manage species. | Names plus species properties such as initial amount and units. | Confirmation or species data. |
| `create_reaction`, `modify_reaction`, `remove_reaction`, `list_reactions` | Manage reactions and rate expressions. | Reactants, products, reversibility, rate law fields. | Confirmation or reaction data. |
| `create_parameter`, `modify_parameter`, `remove_parameter`, `list_parameters` | Manage model parameters. | Names, values, units, and scope. | Confirmation or parameter data. |
| `get_simulation_settings`, `configure_simulation`, `simulate_model` | Inspect, configure, and run simulations. | Solver/settings fields, optional `species`, `doses`, `variants`, and output limits. | Current settings or simulation result rows. |
| `create_dose`, `modify_dose`, `remove_dose`, `list_doses` | Manage repeat and schedule doses. | Dose type, target, timing, amount/rate fields. | Confirmation or dose data. |
| `create_variant`, `modify_variant`, `remove_variant`, `list_variants` | Manage named model overrides. | Variant name and full content entries. | Confirmation or variant data. |
| `export_graph`, `export_csv` | Export the same run used by `simulate_model` to PNG or CSV. | Optional path plus optional `species`, `doses`, and `variants`. | File metadata or inline CSV text. |
| `list_series`, `steady_state`, `series_min`, `series_max` | Analyze exported CSV data without rerunning MATLAB. | CSV path and target series name. | Series names or computed values. |
| `pubmed_search`, `pubmed_summary`, `pubmed_article` | Pull literature context from PubMed. | Query, PubMed ID, and summary options. | Search hits, article details, or summaries. |
| `pubmed_fulltext` | Fetch open-access full text (section-labeled) for a PubMed article from PubMed Central. | PubMed ID, optional section filter, reference toggle, and character cap. | Section-labeled full text (Methods/Results/Tables carry kinetics), or the abstract when not open access. |
| `igem_part`, `igem_search`, `igem_search_best` | Look up parts from the iGEM registry. | Exact identifier or free-text query. | Part records or ranked matches. |
| `sabio_search`, `sabio_entry` | Look up measured enzyme kinetics (Km, kcat, Vmax, Ki) from SABIO-RK. | Fielded query or filters (organism, substrate, EC number, parameter type), or an entry id. | Slimmed kinetics entries with as-reported and SI-normalized values plus source publication. |

## Rules

- Ground the model in real science. Use the iGEM Registry tools, PubMed tools, and other reliable sources as needed.
- Ensure the model is complete before running a simulation.
- Ensure all parameters have accurate values and units.
- Ensure each rate law is dimensionally consistent.
- Export results to CSV and PNG when the user needs outputs or analysis.
- Prefer the common reaction patterns above when they fit the biology.
- Use MCP analysis tools whenever possible instead of manually parsing large exported outputs.
