---
name: using-simbiology-mcp
description: Use when building, simulating, or reporting on ANY SimBiology model through the SimBiology MCP. Encodes the model-building completeness rules, the "default until asked" principle for all configuration, and the result-reading discipline that prevent wrong answers.
---

# Using the SimBiology MCP

General guidance for driving the SimBiology MCP on **any** project. The MCP itself is only the set
of tools for manipulating a SimBiology model (species, parameters, compartments, reactions,
simulation, export). All judgment about *how* to use those tools well lives here, not in the MCP.

Nothing below is specific to one model. Where an example is given it is illustrative of a general
pattern, not a template to copy.

---

## Governing principle: default until asked

**Leave every configurable choice at its SimBiology default until the user asks for something
different.** This is a default-not-a-mandate: if the user wants to change it, change it freely and
without pushback. You are not being asked to lock defaults down - you are being asked not to
*silently* diverge from them.

This applies to, at minimum:

- **Solver** (default `ode15s`), **absolute tolerance** (`1e-6`), **relative tolerance** (`1e-3`),
  and **maximum number of logs** (`Inf`). Do not change these unless asked or unless the task
  clearly requires it.
- **Stop time** - leave the default unless the task specifies a simulation duration.
- **Output/time grid, plotting choices, file paths, units of display** - default unless asked.
- **Initial amounts/concentrations** - whatever the model/problem defines; don't invent them.

If the user says "I want RelTol at 1e-6" or "use ode23t" or "simulate for 5000 minutes" - do
exactly that. The rule is *don't diverge from default on your own initiative*, not *never diverge*.

This principle is what keeps the skill unbiased: it works for the person who wants stock behavior
and the person who wants full manual control.

## Model-building completeness (NOT optional, never "default until asked")

Configuration is left at default; **model correctness is not**. A model must be built completely and
correctly every time. The following are requirements, not preferences:

- **Create EVERY parameter the model references.** A rate law that names a constant requires that
  constant to exist as a parameter. Missing parameters are the most common build error.
- **Give EVERY parameter its units.** Set units on each parameter to match the source
  (`1/minute`, `molarity`, `molarity/minute`, `1/(minute*molarity)`, `kelvin`, dimensionless, etc.).
  A parameter with no units is a defect, even if the number is right. (In the first pass on a model
  it is easy to create parameters and forget the units - check every one before simulating.)
- **Give species their correct units/dimension** (amount vs. concentration) and initial values.
- **Set the compartment volume/capacity whenever the problem gives one.** If a cell volume,
  reactor volume, or compartment size is specified, enter it. Always support setting it; never
  assume it is 1 and never assume it is irrelevant. It is part of a faithful model.
- **Build every reaction the biology/chemistry requires** - see the correctness rules below.

Think of it as two separate concerns: *is the model a faithful, complete representation?* (always
yes) versus *which optional settings did I change?* (none, unless asked).

## The compartment volume - set it, and understand when it matters

- **If the problem gives a compartment/cell volume, set it.** This is always allowed and usually
  expected. Do not skip it and do not hardcode assumptions from some other project.
- **Do not divide rate constants by the volume unless the rate law explicitly says to.** Enter
  given rate constants as given. Inventing a volume division is a modeling error.
- **Know the dimensional behavior:** for concentration-dimension (molarity) species in a single
  compartment, `d[S]/dt = reaction rate` - the compartment volume does not divide the rate, so
  setting the volume is faithful bookkeeping but won't rescale a concentration result. For
  amount-dimension species, volume does enter concentration conversions. Either way: set the volume
  when given; don't use it to fudge rate constants.

## Simulation settings - the one footgun to know

Even though settings are left at default, know **why** one default matters:

- **`MaximumNumberOfLogs` is a STOP condition, not a verbosity control.** The run halts once that
  many points are logged. If it is set low, the simulation stops early and every species reads a
  not-yet-converged value - which looks exactly like a broken model. Leave it at the default (`Inf`)
  unless the user asks otherwise. If you want a smaller returned payload, request fewer species or
  read only the final point - do **not** lower the log cap to achieve that.
- If a run's final time point is far below the stop time, the run was **truncated** - re-check the
  log cap and stop time before interpreting any value.

## Reading results correctly

- **A steady-state value is the last point of the returned trace**, converted into the units the
  question uses (raw output is mol/L; x1e9 -> nM, x1e6 -> uM).
- If a value is off by orders of magnitude from an expectation, suspect **settings (truncation) or
  units first - not the reactions.** The model is usually right. Do not jump to an external
  Python/MATLAB replica as a "workaround"; that hides the real cause instead of fixing it.
- "Time to steady state" = first time the curve is within ~0.1% of its final value.

## Export discipline

- **Use the MCP export tools for deliverables.** If the user wants a plot or CSV, use
  `export_graph` / `export_csv` with their labeling and column options instead of writing ad hoc
  MATLAB scripts, PowerShell, Python, or Matplotlib helpers on the side.
- If the current export tool surface is missing a needed option, **extend the MCP/export tool**
  rather than escaping into one-off scripts. The durable fix is better tool capability, not a
  parallel plotting path the next agent will rediscover badly.
- When exporting a figure, set a meaningful title and axis labels when the task implies them.
  Avoid leaving the default generic "States" style output if the question is about a named
  quantity, condition, or unit.

## State mutation - restore what you change

- `modify_parameter` / `modify_species` **persist** on the model. After a sweep (e.g. varying a
  binding constant, stepping temperature, scaling a rate) the model is left modified, which corrupts
  later runs and anything you save.
- **Restore every parameter/species you changed**, or record the originals first and set them back.
- Prefer **variants** for alternate conditions. Per-run `variants`/`species`/`doses` are honored by
  simulation and export **without mutating** the base model - the clean way to run scenarios.

## Model-building correctness rules (generic)

All of these are general modeling requirements, independent of any specific project:

- **Every expressed protein needs its full chain:** transcription (-> mRNA), translation
  (mRNA -> protein), and the corresponding degradation/loss reactions. Don't give a protein a
  translation step with no mRNA.
- **Catalysis does not consume the catalyst.** In an enzymatic step the enzyme appears on **both
  sides** (`S + E -> P + E`), with rate e.g. `kcat*E*S/(Km+S)`. Writing `S + E -> P` is wrong.
- **A reversible complex is ONE reversible reaction:** `A + B <-> AB`, `reversible = true`, rate
  `k_a*A*B - k_d*AB`. Don't model association without dissociation.
- **Don't invent parameters or terms that the problem doesn't define** (including spurious volume
  divisions). If a value is given, use it as given.
- **Hill activation with h=1** is `R/(K+R)`. General Hill is `R^h/(K^h+R^h)`.
- **Logistic/temperature activation** is `1/(1+exp(-(x-x_half)/s))` - the scale `s` **divides**
  `(x-x_half)`. Convert units to match the half-point (e.g. C->K if the half-point is in kelvin).
  Sign and divide-vs-multiply errors silently shift the curve.

## Cumulative / multi-stage models

- When a downstream reaction **drains** an intermediate, that intermediate's steady state in the
  full model is lower than in the isolated sub-model.
- Answer a stage-specific question on that stage's circuit. To read the undrained value, disable
  the draining reaction (set its rate to 0) or simulate the sub-stage - don't report the drained
  full-model value as if it were the isolated one.

## Saving projects

- After `save_project`, check `list_models` for accidental **duplicate models**; save a clean
  single-model project rather than accumulating copies.
- If the user needs to press Run in the SimBiology desktop GUI, note that a project may need a
  simulation **Program/analysis task** present to be runnable - tell them rather than letting them
  hit "No Program in Project."

## Pre-flight checklist (run before reporting any number)

1. **Completeness:** all referenced parameters created, all with units; species dimensions/initials
   set; compartment volume set if given.
2. **Settings:** left at default unless the user asked otherwise; `max_number_of_logs` not lowered;
   run reached its stop time (not truncated).
3. **Reading:** used the **final** time point, in the **right units**.
4. **State:** restored any parameter/species changed during a sweep.
5. **Correctness:** enzyme on both sides of catalysis, complexes reversible, no invented terms or
   volume divisions, Hill/logistic forms right.
6. **Staging:** for a stage-specific value, accounted for any downstream draining.
