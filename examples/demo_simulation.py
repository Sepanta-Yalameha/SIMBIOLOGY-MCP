"""Manual demo of the simulation feature, driving the real core code.

Builds a tiny 1-compartment PK model (Drug -> Metabolite, first-order),
configures the solver, runs the simulation through SbioModel.simulate(), prints
the time course, and opens a live MATLAB plot window so you can see it.

Run from the repo root with the project venv:

    $env:PYTHONPATH = (Get-Location).Path
    .\.venv\Scripts\python.exe .\demo_simulation.py
"""

from core.sbio_service import SbioService
from engine.matlab_layer import MatlabLayer


def main() -> None:
    print("Launching MATLAB (first call is slow)...")
    svc = SbioService()                    # starts the MATLAB engine
    svc.create_project("pk_demo")          # fresh project with one model
    model = svc.get_model()

    # --- build the model via the builder/executor convention ---
    svc.execute(model.add_compartment_cmd("central"))
    svc.execute(model.add_species_cmd("central", "Drug", 100))
    svc.execute(model.add_species_cmd("central", "Metabolite", 0))
    svc.execute(model.add_parameter_cmd("ke", 0.3))
    svc.execute(model.add_reaction_cmd("elimination", "Drug -> Metabolite; ke*Drug"))

    print("\nspecies  :", model.species())
    print("reactions:", model.reactions())
    print("params   :", model.parameters())

    # --- configure the simulation (what the MCP configure_simulation tool does) ---
    svc.execute(model.set_configset_cmd(stop_time=20, solver_type="ode45"))
    print("\nsettings :", model.get_configset())

    # --- run it (what simulate_model does) ---
    result = model.simulate()
    times = result["time"]
    drug = result["data"]["Drug"]
    metab = result["data"]["Metabolite"]

    print(f"\nsimulated {len(times)} time points over "
          f"{times[0]}-{times[-1]} {result['time_units']}")
    print(f"{'t':>6} {'Drug':>10} {'Metabolite':>12}")
    for i in range(0, len(times), max(1, len(times) // 10)):
        print(f"{times[i]:6.2f} {drug[i]:10.4f} {metab[i]:12.4f}")
    print(f"\nmass check Drug+Metabolite (start): {drug[0] + metab[0]:.3f}")
    print(f"mass check Drug+Metabolite (end)  : {drug[-1] + metab[-1]:.3f}")

    # --- show it in MATLAB ---
    svc.execute("sbioplot(sbio_sd); drawnow; saveas(gcf,'sim_demo.png');")
    print("\nSaved plot to sim_demo.png and opened a MATLAB figure window.")
    input("Press Enter to close MATLAB and exit...")
    MatlabLayer().exit()


if __name__ == "__main__":
    main()
