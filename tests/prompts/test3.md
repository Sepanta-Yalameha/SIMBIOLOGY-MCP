Using the SimBiology MCP tools ONLY, build, simulate, and export a reduced digital
twin of engineered *Escherichia coli* producing a **recombinant protein** under an
inducible promoter, with growth dilution and metabolic burden, in:

projects/ecoli_production/

Execute every step with MCP tools. This is a determinism probe: build exactly the
reduced model specified below (do not add extra pathways), and research the numeric
parameters rather than inventing them.

## The system (build exactly this reduced topology)
- **Inducible expression:** promoter -> target **mRNA** -> target **Protein** (the
  recombinant product). Induction increases transcription via a Hill activation term
  in the transcription rate expression.
- **Plasmid copy number:** a parameter `copy_number` that multiplies the
  transcription rate (more plasmid -> more transcription).
- **Growth and dilution:** a `growth_rate` parameter that dilutes EVERY species by a
  first-order loss term (loss = growth_rate * species).
- **Metabolic burden (choose ONE mechanism and use only it):** make `growth_rate`
  decrease as the product accumulates, expressed through a rate law (e.g.
  growth_rate_effective = growth_rate_max / (1 + Product/burden_K)). Do not add a
  second burden mechanism.

## Research (use the MCP tools; cite everything)
- `pubmed_*`: transcription and translation rates, mRNA and protein degradation
  rates, E. coli maximal growth rate, typical plasmid copy numbers (low vs high),
  and a burden coefficient. Convert half-lives to rate constants.
- `igem_part`: select the promoter, RBS, product CDS, and terminator parts; record
  their IDs.

## Scenarios (use `create_variant`)
- `low_copy` and `high_copy`: `copy_number` set to your researched low vs high
  plasmid values.
- `no_burden`: the burden coefficient set so burden is off (control).

## Simulate (deterministic ode15s)
- Choose a stop time long enough to reach steady state and state it.
- Run: baseline, `low_copy` vs `high_copy`, and `no_burden` vs baseline.

## Outputs
- Report the steady-state **product yield** and the final `growth_rate` for each
  scenario, and explain the copy-number vs burden trade-off in one or two sentences.
- `export_graph` of product vs time across the copy-number variants ->
  projects/ecoli_production/copy_number.png
- `export_csv` of the product time-course -> projects/ecoli_production/product.csv
- Save the project -> projects/ecoli_production/model.sbproj

## Constraints
- Deterministic ODE only.
- Use only compartments, species, parameters, reactions, variants, simulate, and
  export (no rules/events/observables/SBML).
- Exactly one burden mechanism; every numeric parameter must be sourced from PubMed
  or an iGEM part.
