You are given the file **`Sample SimBiology Test1.pdf`** (in this same folder). This
is a real SimBiology modeling test (McMaster IBEHS 2PB2) with a tiered, four-level
structure. Read the PDF in full before doing anything, including:
- all instructional text,
- the **parameter table (Table 1)**, and
- **every SBOL diagram (Figures 1 through 5)**.

The circuit topology is defined by the SBOL diagrams, not by prose. You must
interpret the SBOL glyphs yourself (promoters, RBS, coding sequences, terminators,
repression vs activation arrows, complex formation "+", and catalysis) to derive the
species and reactions for each level. Getting the structure right from the figures
is a graded part of this test.

## What to do
Using the SimBiology MCP tools ONLY, complete the test exactly as the PDF specifies
(do not describe steps; execute them via tools).

- Name the model **`X_Detector`** and save it to projects/x_detector/model.sbproj.
- Build the circuit **cumulatively** across all four levels: start from the Level 1
  cassette and, for each higher level, ADD the components shown in that level's SBOL
  figure to the SAME model (reuse lower-level work; do not rebuild).
- Use the **exact values, units, initial conditions, and simulation settings from
  the PDF**: every parameter from Table 1, all species initial concentrations of 0,
  molarity units throughout, and a simulation time of 1000 minutes. Do NOT research
  or invent any parameter; the PDF provides them all.
- Model the specified kinetics precisely:
  - **logistic** temperature activation of the Temp promoter (using Temp_half and
    Sigma; convert temperature with K = degreesC + 273),
  - **Michaelis-Menten** catalysis for Enzyme B (Km, kcat),
  - **Hill coefficient = 1** (no cooperativity) for all regulated transcription,
  - biomarker/toehold activation via K_X, and AD-complex association/dissociation
    (k_a, k_d),
  - the shared loss rates k_mRNA_loss and k_pro_loss.
- Answer **every numbered question in all four levels** (steady-state
  concentrations, approximate times to steady state, and the parameter-perturbation
  questions such as "decrease K_X by 10x"). Report results clearly, grouped by level
  and question number. The perturbation and per-condition questions are natural fits
  for `create_variant` (e.g. one variant per temperature or per perturbed constant).
- Produce **every exported graph each level requires**, properly labeled and
  captioned, with `export_graph`, and export the underlying time-course with
  `export_csv`. Save all figures and CSVs under projects/x_detector/.

## Notes
- This is both a **figure-comprehension test** (your circuit must match the SBOL
  diagrams) and a **determinism test** (because all parameters are given, your
  numeric answers should be reproducible run to run).
- Use only the capabilities this MCP provides: compartments, species, parameters,
  reactions (with arbitrary rate expressions for the logistic and Michaelis-Menten
  kinetics), doses, variants, configure/simulate, and export.
