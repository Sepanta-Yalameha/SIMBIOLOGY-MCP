---
name: simbiology-workflow
description: Use when building, modifying, simulating, exporting, or analyzing MATLAB SimBiology models through the SimBiology MCP. Covers project setup, species, parameters, reactions, doses, variants, simulation defaults, export, analysis, and use of PubMed and iGEM tools to ground model constants in real biology.
---

# SimBiology Workflow

Use this skill when the user wants to model or simulate a genetic circuit, synthetic biology system, PK/PD system, or related biochemical network through the SimBiology MCP.

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
- All internal species should generally have a loss or degradation reaction.
- A pure external input signal may be exempt from degradation if that is the intended assumption.
- Do not create unused parameters unless they have a clear purpose in the model.
- Validate constants with iGEM, PubMed, or other scientific sources when possible.

***Major correction: every species should not merely "interact with the rest of the simulation"; it should have the specific production, consumption, and loss processes required by the biology.***

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

***Major addition: variants are for alternate named model states, while doses are for changes applied during a run over time.***

## Export and Analysis

After simulation:

- export the results to CSV
- export the graph to PNG
- use the analysis MCP tools whenever possible instead of manually scanning large outputs
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
| Toe-hold-switch-regulated translation | `mRNA_B -> mRNA_B + B` with reaction name like `B_trsl` | `k_trsl_B*((X/K_X)/(1+X/K_X))` | `k_trsl_B`, `K_X`, species `X` | Use when the coding sequence / translation step is positively regulated by a biomarker or toe-hold switch. |
| Negative regulator on translation | `mRNA_B -> mRNA_B + B` with reaction name like `B_trsl` | `k_trsl_B*(1/(1+R/K_R))` | `k_trsl_B`, `K_R`, species `R` | Use when a coding sequence or translation step is negatively regulated. |
| Heat-activated temperature-dependent transcription | `null -> mRNA_C` with reaction name like `C_trsc` | `k_trsc_C*(1/(1+exp(-(Temp-Temp_half)/sigma)))` | `k_trsc_C`, `Temp`, `Temp_half`, `sigma` | Use when higher temperature increases promoter activity. `Temp` is typically in Kelvin. |
| Cold-activated temperature-dependent transcription | `null -> mRNA_C` with reaction name like `C_trsc` | `k_trsc_C*(1/(1+exp((Temp-Temp_half)/sigma)))` | `k_trsc_C`, `Temp`, `Temp_half`, `sigma` | Use when lower temperature increases promoter activity. This is the inverse orientation of the heat-activated logistic form. |
| Michaelis-Menten catalysis | `B + C -> B + D` with reaction name like `Catalysis` | `kcat*B*C/(Km+C)` | `kcat`, `Km` | The catalyst is not consumed, so it appears on both sides. |
| Reversible complexation | `A + D <-> AD` with reaction name like `Complexation` | `ka*A*D - kd*AD` | `ka`, `kd` | Use for reversible binding / complex formation. |
| General Hill-style regulation | Varies by system | use the problem-specific activation or repression expression | regulator constant(s), Hill coefficient if needed, base rate constant | Use when the system statement explicitly describes promoter or coding-sequence regulation. |

Use the correct rate law for the biology. Do not force a reaction into a mass-action interpretation if the biology requires a custom rate expression. In this MCP, reaction creation supports a reaction equation plus a `rate` expression; it does not expose a separate kinetic-law selector. In practice, that means:

- use plain mass-action-style rate expressions when the biology is truly mass action
- use custom rate expressions when the biology calls for Hill regulation, Michaelis-Menten behavior, temperature dependence, or other non-mass-action behavior
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
| Toe-hold-switch-regulated translation | `rate = k_trsl_B*((X/K_X)/(1+X/K_X))` |
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
- pH-style regulation should be framed in terms of `[H+]`, not informal “low pH vs high pH” language alone. If the system activates as pH drops, that means it is **H+-activated** because `[H+]` increases as pH decreases.
- Heat-dependent and cold-dependent regulation use opposite logistic orientations; choose the sign that matches whether activity should increase with higher temperature or lower temperature.

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
| `igem_part`, `igem_search`, `igem_search_best` | Look up parts from the iGEM registry. | Exact identifier or free-text query. | Part records or ranked matches. |

## Rules

- Ground the model in real science. Use the iGEM Registry tools, PubMed tools, and other reliable sources as needed.
- Ensure the model is complete before running a simulation.
- Ensure all parameters have accurate values and units.
- Ensure each rate law is dimensionally consistent.
- Export results to CSV and PNG when the user needs outputs or analysis.
- Prefer the common reaction patterns above when they fit the biology.
- Use MCP analysis tools whenever possible instead of manually parsing large exported outputs.

***Major correction: this skill should guide the agent toward the MCP tool surface first, not toward ad hoc manual analysis or external scripting unless the MCP tools are missing a needed capability.***
