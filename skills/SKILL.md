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
| Transcription | `source -> mRNA` | Usually constant or promoter-specific | transcription rate constant | Use for gene expression into mRNA. |
| Translation | `mRNA -> Protein` | Usually proportional to mRNA | translation rate constant | Use for production of protein from mRNA. |
| mRNA loss | `mRNA -> null` | `k_deg_mRNA * mRNA` | mRNA degradation constant | The cheat sheet notes these are generally similar across mRNA species if the model assumes shared degradation constants. |
| Protein loss | `Protein -> null` | `k_deg_protein * Protein` | protein degradation constant | Use for natural loss/degradation of proteins. |
| Toe-hold-switch-regulated translation | `mRNA -> Protein` | Hill-style or other regulator-dependent translation law | regulator constant such as `K_X`, translation constant, Hill coefficient if needed | Use when the toe-hold switch changes translation behavior rather than transcription. The regulator reveals the binding site and controls translation. |
| Input-regulated transcription or translation / Hill regulation | Varies by system | Hill-style regulatory law | regulator constant, Hill coefficient if needed, base rate constant | Use when a regulator, inducer, or repressor changes expression behavior. |
| Temperature-dependent transcription | `source -> mRNA` | custom temperature-dependent law | temperature term(s), threshold/shape constants, transcription constant | The cheat sheet explicitly says this is not mass action when transcription depends on temperature. |
| Michaelis-Menten catalysis | `Substrate + Enzyme -> Product + Enzyme` | Michaelis-Menten form | `kcat`, `Km` | The catalyst must appear on both sides because it is not consumed. |
| Reversible complexation | `A + B <-> AB` | forward association minus reverse dissociation | `k_a`, `k_d` | Use one reversible reaction when appropriate. Forward is association, reverse is dissociation. |
| Positive induction by complex/regulator | `source -> mRNA` or regulated production step | Hill activation law | regulator constant, Hill coefficient if needed, production constant | Use when a complex such as `AD` positively induces downstream expression. |

Use the correct rate law for the biology. Do not force a reaction into a mass-action interpretation if the biology requires a custom rate expression. In this MCP, reaction creation supports a reaction equation plus a `rate` expression; it does not expose a separate kinetic-law selector. In practice, that means:

- use plain mass-action-style rate expressions when the biology is truly mass action
- use custom rate expressions when the biology calls for Hill regulation, Michaelis-Menten behavior, temperature dependence, or other non-mass-action behavior
- do not treat an "unknown reaction" style warning as a reason to simplify the biology incorrectly; keep the accurate rate expression

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
