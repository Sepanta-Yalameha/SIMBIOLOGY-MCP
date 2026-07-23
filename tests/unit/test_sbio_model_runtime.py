from __future__ import annotations

from pathlib import Path

import pytest

from simbiology_mcp.core.sbio_model import SbioModel
from simbiology_mcp.engine.exceptions import ElementNotFoundError


class FakeService:
    def __init__(self) -> None:
        self.commands: list[str] = []
        self.values: dict[tuple[str, int], object] = {}

    def execute(self, command: str, nargout: int = 0):
        self.commands.append(command)
        key = (command, nargout)
        if key in self.values:
            return self.values[key]
        raise AssertionError(f"Unexpected execute call: {key!r}")


@pytest.fixture
def service() -> FakeService:
    return FakeService()


@pytest.fixture
def model(service: FakeService) -> SbioModel:
    return SbioModel(service=service, var="m", name="demo")


def test_names_and_detail_reads(model: SbioModel, service: FakeService) -> None:
    service.values[("{m.Species.Name}", 1)] = ["A", "B"]
    service.values[("{m.Reactions.Name}", 1)] = ["rx"]
    service.values[("{m.Compartments.Name}", 1)] = ["cell"]
    service.values[("{m.Parameters.Name}", 1)] = ["k1"]
    service.values[("{m.Doses.Name}", 1)] = ["d1"]
    service.values[("{m.Variants.Name}", 1)] = ["v1"]
    service.values[("sbio_e = sbioselect(m,'Type','species','Name','A');", 0)] = None
    service.values[("isempty(sbio_e)", 1)] = False
    service.values[("struct('Name',sbio_e.Name,'Value',sbio_e.Value,'Units',sbio_e.InitialAmountUnits,'Compartment',sbio_e.Parent.Name)", 1)] = {
        "Name": "A",
        "Value": 1.0,
        "Units": "molarity",
        "Compartment": "cell",
    }

    assert model.species() == ["A", "B"]
    assert model.reactions() == ["rx"]
    assert model.compartments() == ["cell"]
    assert model.parameters() == ["k1"]
    assert model.doses() == ["d1"]
    assert model.variants() == ["v1"]
    assert model.get_species("A") == {"Name": "A", "Value": 1.0, "Units": "molarity", "Compartment": "cell"}


def test_detail_and_named_helpers_raise_on_missing(model: SbioModel, service: FakeService) -> None:
    service.values[("sbio_e = sbioselect(m,'Type','reaction','Name','rx');", 0)] = None
    service.values[("isempty(sbio_e)", 1)] = True

    with pytest.raises(ElementNotFoundError, match="No reaction named"):
        model.get_reaction("rx")

    with pytest.raises(ElementNotFoundError, match="No dose\\(s\\) \\['missing'\\]"):
        model._require_named("dose", ["d1"], ["missing"])

    assert model._name_array("getdose", None) == "[]"
    assert model._name_array("getdose", ["d1", "d2"]) == "[getdose(m,'d1'),getdose(m,'d2')]"


def test_get_dose_reads_repeat_and_schedule_shapes(model: SbioModel, service: FakeService) -> None:
    service.values[("sbio_e = getdose(m,'repeat');", 0)] = None
    service.values[("isempty(sbio_e)", 1)] = False
    service.values[("class(sbio_e)", 1)] = "SimBiology.RepeatDose"
    service.values[("sbio_e.Name", 1)] = "repeat"
    service.values[("sbio_e.TargetName", 1)] = "Drug"
    service.values[("sbio_e.Amount", 1)] = 10.0
    service.values[("sbio_e.StartTime", 1)] = 0.0
    service.values[("sbio_e.Interval", 1)] = 8.0
    service.values[("sbio_e.RepeatCount", 1)] = 2.0
    service.values[("sbio_e.Rate", 1)] = 0.0
    service.values[("sbio_e.AmountUnits", 1)] = "milligram"
    service.values[("sbio_e.RateUnits", 1)] = "milligram/hour"
    service.values[("sbio_e.TimeUnits", 1)] = "hour"

    repeat = model.get_dose("repeat")
    assert repeat["Type"] == "repeat"
    assert repeat["Interval"] == 8.0

    service.values[("sbio_e = getdose(m,'sched');", 0)] = None
    service.values[("class(sbio_e)", 1)] = "SimBiology.ScheduleDose"
    service.values[("sbio_e.Name", 1)] = "sched"
    service.values[("sbio_e.TargetName", 1)] = "Drug"
    service.values[("sbio_e.Time", 1)] = [0.0, 1.0]
    service.values[("sbio_e.Amount", 1)] = [2.0, 3.0]
    service.values[("sbio_e.Rate", 1)] = [0.0, 0.0]

    sched = model.get_dose("sched")
    assert sched["Type"] == "schedule"
    assert sched["Time"] == [0.0, 1.0]


def test_get_variant_and_configset_reads(model: SbioModel, service: FakeService) -> None:
    service.values[("sbio_e = getvariant(m,'v1');", 0)] = None
    service.values[("isempty(sbio_e)", 1)] = False
    service.values[("sbio_e.Name", 1)] = "v1"
    service.values[("sbio_e.Active", 1)] = True
    service.values[("sbio_e.Content", 1)] = [["parameter", "k1", "Value", 2.0]]
    service.values[("sbio_cs = getconfigset(m);", 0)] = None
    service.values[
        (
            "struct('StopTime',sbio_cs.StopTime,'SolverType',sbio_cs.SolverType,'TimeUnits',sbio_cs.TimeUnits,'MaximumWallClock',sbio_cs.MaximumWallClock,'MaximumNumberOfLogs',sbio_cs.MaximumNumberOfLogs)",
            1,
        )
    ] = {
        "StopTime": 10.0,
        "SolverType": "ode15s",
        "TimeUnits": "hour",
        "MaximumWallClock": float("inf"),
        "MaximumNumberOfLogs": 1000,
    }
    service.values[("isprop(sbio_cs.SolverOptions,'AbsoluteTolerance')", 1)] = True
    service.values[("sbio_cs.SolverOptions.AbsoluteTolerance", 1)] = 1e-6
    service.values[("sbio_cs.SolverOptions.RelativeTolerance", 1)] = 1e-3

    assert model.get_variant("v1")["Active"] is True
    settings = model.get_configset()
    assert settings["MaximumWallClock"] is None
    assert settings["AbsoluteTolerance"] == 1e-6


def test_simulate_and_export_plot_paths(model: SbioModel, service: FakeService, tmp_path: Path) -> None:
    service.values[("{m.Doses.Name}", 1)] = ["d1"]
    service.values[("{m.Variants.Name}", 1)] = ["v1"]
    service.values[
        (
            "sbio_sd = sbiosimulate(m,getconfigset(m),[getvariant(m,'v1')],[getdose(m,'d1')]);",
            0,
        )
    ] = None
    service.values[("sbio_sd_sel = selectbyname(sbio_sd,{'A','B'});", 0)] = None
    service.values[("sbio_sd_sel.Time", 1)] = [0.0, 1.0]
    service.values[("sbio_sd_sel.Data", 1)] = [[5.0, 1.0], [3.0, 2.0]]
    service.values[("sbio_sd_sel.DataNames", 1)] = ["A", "B"]
    service.values[("sbio_sd_sel.TimeUnits", 1)] = "hour"
    service.values[("sbio_ax = sbioplot(sbio_sd_sel);", 0)] = None
    service.values[("title(sbio_ax,'Run');", 0)] = None
    service.values[("xlabel(sbio_ax,'Time');", 0)] = None
    service.values[("ylabel(sbio_ax,'Amount');", 0)] = None
    service.values[("legend(sbio_ax,{'A','B'});", 0)] = None
    service.values[("sbio_fig = get(sbio_ax,'Parent');", 0)] = None
    out = tmp_path / "plot.png"
    service.values[(f"exportgraphics(sbio_fig,'{str(out)}','Resolution',300);", 0)] = None
    service.values[("close(sbio_fig);", 0)] = None

    result = model.simulate(species=["A", "B"], doses=["d1"], variants=["v1"])
    assert result["data"]["A"] == [5.0, 3.0]

    exported = model.export_plot(str(out), species=["A", "B"], doses=["d1"], variants=["v1"], title="Run", x_label="Time", y_label="Amount", legend_labels=["A", "B"])
    assert exported == {"path": str(out), "resolution": 300}


def test_export_plot_rejects_mismatched_legend_length(model: SbioModel, service: FakeService) -> None:
    service.values[("sbio_sd = sbiosimulate(m);", 0)] = None
    service.values[("sbio_sd.DataNames", 1)] = ["A", "B"]

    with pytest.raises(ValueError, match="legend_labels must match"):
        model.export_plot("out.png", legend_labels=["only-one"])


# --- multi-run overlays ---
def test_export_overlay_plot_builds_distinct_run_vars(model: SbioModel, service: FakeService, tmp_path: Path) -> None:
    service.values[("{m.Variants.Name}", 1)] = ["low", "high"]
    service.values[("sbio_run_1 = sbiosimulate(m,getconfigset(m),[getvariant(m,'low')],[]);", 0)] = None
    service.values[("sbio_run_1_sel = selectbyname(sbio_run_1,{'GFP'});", 0)] = None
    service.values[("sbio_run_1_sel.DataNames", 1)] = "GFP"
    service.values[("sbio_run_2 = sbiosimulate(m,getconfigset(m),[getvariant(m,'high')],[]);", 0)] = None
    service.values[("sbio_run_2_sel = selectbyname(sbio_run_2,{'GFP'});", 0)] = None
    service.values[("sbio_run_2_sel.DataNames", 1)] = "GFP"
    service.values[("sbio_ax = sbioplot([sbio_run_1_sel sbio_run_2_sel]);", 0)] = None
    service.values[("legend(sbio_ax,{'low','high'});", 0)] = None
    service.values[("sbio_fig = get(sbio_ax,'Parent');", 0)] = None
    out = tmp_path / "overlay.png"
    service.values[(f"exportgraphics(sbio_fig,'{str(out)}','Resolution',300);", 0)] = None
    service.values[("close(sbio_fig);", 0)] = None

    result = model.export_overlay_plot(
        str(out),
        runs=[{"label": "low", "variants": ["low"]}, {"label": "high", "variants": ["high"]}],
        species=["GFP"],
    )

    assert result == {"path": str(out), "resolution": 300, "runs": ["low", "high"]}
    # each run simulated into its own distinct workspace variable (no collision)
    assert "sbio_run_1 = sbiosimulate(m,getconfigset(m),[getvariant(m,'low')],[]);" in service.commands
    assert "sbio_run_2 = sbiosimulate(m,getconfigset(m),[getvariant(m,'high')],[]);" in service.commands
    # the runs are gathered into one SimData array and overlaid by sbioplot
    assert "sbio_ax = sbioplot([sbio_run_1_sel sbio_run_2_sel]);" in service.commands
    # the legend command carries both run labels
    legend_cmds = [c for c in service.commands if c.startswith("legend(")]
    assert legend_cmds == ["legend(sbio_ax,{'low','high'});"]


def test_simulate_overlay_grid_resamples_each_run_onto_shared_grid(model: SbioModel, service: FakeService) -> None:
    service.values[("{m.Variants.Name}", 1)] = ["low", "high"]
    service.values[("sbio_cs = getconfigset(m);", 0)] = None
    service.values[("sbio_cs.StopTime", 1)] = 10.0
    service.values[("sbio_grid = linspace(0,10.0,3)';", 0)] = None
    service.values[("sbio_grid", 1)] = [[0.0], [5.0], [10.0]]
    service.values[("sbio_run_1 = sbiosimulate(m,getconfigset(m),[getvariant(m,'low')],[]);", 0)] = None
    service.values[("sbio_run_1_sel = selectbyname(sbio_run_1,{'GFP'});", 0)] = None
    service.values[("sbio_run_1_al = resample(sbio_run_1_sel,sbio_grid);", 0)] = None
    service.values[("sbio_run_1_al.DataNames", 1)] = "GFP"
    service.values[("sbio_run_1_al.Data", 1)] = [[1.0], [2.0], [3.0]]
    service.values[("sbio_run_1_al.TimeUnits", 1)] = "second"
    service.values[("sbio_run_2 = sbiosimulate(m,getconfigset(m),[getvariant(m,'high')],[]);", 0)] = None
    service.values[("sbio_run_2_sel = selectbyname(sbio_run_2,{'GFP'});", 0)] = None
    service.values[("sbio_run_2_al = resample(sbio_run_2_sel,sbio_grid);", 0)] = None
    service.values[("sbio_run_2_al.DataNames", 1)] = "GFP"
    service.values[("sbio_run_2_al.Data", 1)] = [[4.0], [5.0], [6.0]]

    result = model.simulate_overlay_grid(
        runs=[{"label": "low", "variants": ["low"]}, {"label": "high", "variants": ["high"]}],
        species=["GFP"],
        output_points=3,
    )

    # resample runs exactly once per run, both onto the same shared grid
    resample_cmds = [c for c in service.commands if c.startswith(("sbio_run_1_al = resample", "sbio_run_2_al = resample"))]
    assert resample_cmds == [
        "sbio_run_1_al = resample(sbio_run_1_sel,sbio_grid);",
        "sbio_run_2_al = resample(sbio_run_2_sel,sbio_grid);",
    ]
    assert result["time"] == [0.0, 5.0, 10.0]
    # single-species runs key their column on the run label; equal row counts
    assert [name for name, _ in result["columns"]] == ["low", "high"]
    assert result["columns"][0] == ("low", [1.0, 2.0, 3.0])
    assert result["columns"][1] == ("high", [4.0, 5.0, 6.0])
    assert result["labels"] == ["low", "high"]


def test_simulate_overlay_grid_names_multi_species_columns(model: SbioModel, service: FakeService) -> None:
    service.values[("sbio_cs = getconfigset(m);", 0)] = None
    service.values[("sbio_cs.StopTime", 1)] = 10.0
    service.values[("sbio_grid = linspace(0,10.0,2)';", 0)] = None
    service.values[("sbio_grid", 1)] = [[0.0], [10.0]]
    service.values[("sbio_run_1 = sbiosimulate(m);", 0)] = None
    service.values[("sbio_run_1_sel = selectbyname(sbio_run_1,{'GFP','RFP'});", 0)] = None
    service.values[("sbio_run_1_al = resample(sbio_run_1_sel,sbio_grid);", 0)] = None
    service.values[("sbio_run_1_al.DataNames", 1)] = ["GFP", "RFP"]
    service.values[("sbio_run_1_al.Data", 1)] = [[1.0, 10.0], [2.0, 20.0]]
    service.values[("sbio_run_1_al.TimeUnits", 1)] = "second"

    result = model.simulate_overlay_grid(runs=[{"label": "wt", "species": ["GFP", "RFP"]}], output_points=2)

    # a multi-species run keys each column on "<label>_<species>"
    assert [name for name, _ in result["columns"]] == ["wt_GFP", "wt_RFP"]
    assert result["columns"][0] == ("wt_GFP", [1.0, 2.0])
    assert result["columns"][1] == ("wt_RFP", [10.0, 20.0])


def test_simulate_overlay_grid_rejects_colliding_column_keys(model: SbioModel, service: FakeService) -> None:
    # Unique labels, but the derived column keys collide: run 1 (single species)
    # keys on "A_B" and run 2's first species keys on "A" + "_" + "B" == "A_B".
    service.values[("sbio_cs = getconfigset(m);", 0)] = None
    service.values[("sbio_cs.StopTime", 1)] = 10.0
    service.values[("sbio_grid = linspace(0,10.0,2)';", 0)] = None
    service.values[("sbio_grid", 1)] = [[0.0], [10.0]]
    service.values[("sbio_run_1 = sbiosimulate(m);", 0)] = None
    service.values[("sbio_run_1_sel = selectbyname(sbio_run_1,{'C'});", 0)] = None
    service.values[("sbio_run_1_al = resample(sbio_run_1_sel,sbio_grid);", 0)] = None
    service.values[("sbio_run_1_al.DataNames", 1)] = "C"
    service.values[("sbio_run_1_al.Data", 1)] = [[1.0], [2.0]]
    service.values[("sbio_run_1_al.TimeUnits", 1)] = "second"
    service.values[("sbio_run_2 = sbiosimulate(m);", 0)] = None
    service.values[("sbio_run_2_sel = selectbyname(sbio_run_2,{'B','D'});", 0)] = None
    service.values[("sbio_run_2_al = resample(sbio_run_2_sel,sbio_grid);", 0)] = None
    service.values[("sbio_run_2_al.DataNames", 1)] = ["B", "D"]
    service.values[("sbio_run_2_al.Data", 1)] = [[3.0, 30.0], [4.0, 40.0]]
    service.values[("sbio_run_2_al.TimeUnits", 1)] = "second"

    with pytest.raises(ValueError, match="duplicate CSV column names"):
        model.simulate_overlay_grid(
            runs=[{"label": "A_B", "species": ["C"]}, {"label": "A", "species": ["B", "D"]}],
            output_points=2,
        )


@pytest.mark.parametrize(
    "runs, match",
    [
        ([], "at least one run"),
        ([{"variants": ["v1"]}], "non-empty 'label'"),
        ([{"label": "  "}], "non-empty 'label'"),
        ([{"label": "x"}, {"label": "x"}], "unique"),
        ([{"label": "x", "variant": ["v"]}], "unknown run key"),  # 'variant' typo, not silently dropped
        (["notadict"], "must be a dict"),
    ],
)
def test_overlay_rejects_bad_run_lists(model: SbioModel, service: FakeService, runs, match) -> None:
    # validation happens before any MATLAB executes, so no commands are recorded
    with pytest.raises(ValueError, match=match):
        model.export_overlay_plot("out.png", runs=runs)
    with pytest.raises(ValueError, match=match):
        model.simulate_overlay_grid(runs=runs)
    assert service.commands == []


def test_export_overlay_plot_rejects_mismatched_legend_labels(model: SbioModel, service: FakeService) -> None:
    for i in (1, 2):
        service.values[(f"sbio_run_{i} = sbiosimulate(m);", 0)] = None
        service.values[(f"sbio_run_{i}_sel = selectbyname(sbio_run_{i},{{'GFP'}});", 0)] = None
        service.values[(f"sbio_run_{i}_sel.DataNames", 1)] = "GFP"

    with pytest.raises(ValueError, match="legend_labels must match"):
        model.export_overlay_plot("out.png", runs=[{"label": "a"}, {"label": "b"}], species=["GFP"], legend_labels=["only-one"])
    # raised after simulating (to know the line count) but before plotting: no figure opened
    assert not any(c.startswith("sbio_ax") for c in service.commands)


def test_export_overlay_plot_rejects_differing_species(model: SbioModel, service: FakeService) -> None:
    service.values[("sbio_run_1 = sbiosimulate(m);", 0)] = None
    service.values[("sbio_run_1_sel = selectbyname(sbio_run_1,{'A'});", 0)] = None
    service.values[("sbio_run_1_sel.DataNames", 1)] = "A"
    service.values[("sbio_run_2 = sbiosimulate(m);", 0)] = None
    service.values[("sbio_run_2_sel = selectbyname(sbio_run_2,{'A','B'});", 0)] = None
    service.values[("sbio_run_2_sel.DataNames", 1)] = ["A", "B"]

    # sbioplot cannot overlay runs with different states; reject before opening a figure
    with pytest.raises(ValueError, match="same species"):
        model.export_overlay_plot("out.png", runs=[{"label": "a", "species": ["A"]}, {"label": "b", "species": ["A", "B"]}])
    assert not any(c.startswith("sbio_ax") for c in service.commands)


def test_simulate_overlay_grid_rejects_row_count_mismatch(model: SbioModel, service: FakeService) -> None:
    service.values[("sbio_cs = getconfigset(m);", 0)] = None
    service.values[("sbio_cs.StopTime", 1)] = 10.0
    service.values[("sbio_grid = linspace(0,10.0,3)';", 0)] = None
    service.values[("sbio_grid", 1)] = [[0.0], [5.0], [10.0]]
    service.values[("sbio_run_1 = sbiosimulate(m);", 0)] = None
    service.values[("sbio_run_1_sel = selectbyname(sbio_run_1,{'A'});", 0)] = None
    service.values[("sbio_run_1_al = resample(sbio_run_1_sel,sbio_grid);", 0)] = None
    service.values[("sbio_run_1_al.DataNames", 1)] = "A"
    service.values[("sbio_run_1_al.Data", 1)] = [[1.0], [2.0]]  # 2 rows, grid has 3

    with pytest.raises(ValueError, match="expected 3"):
        model.simulate_overlay_grid(runs=[{"label": "r", "species": ["A"]}], output_points=3)


def test_simulate_overlay_grid_rejects_nonfinite_stop_time(model: SbioModel, service: FakeService) -> None:
    service.values[("sbio_cs = getconfigset(m);", 0)] = None
    service.values[("sbio_cs.StopTime", 1)] = float("inf")

    with pytest.raises(ValueError, match="finite, positive stop time"):
        model.simulate_overlay_grid(runs=[{"label": "r", "species": ["A"]}])
    # raised before the grid is built
    assert not any(c.startswith("sbio_grid = linspace") for c in service.commands)


def test_simulate_overlay_grid_clamps_output_points(model: SbioModel, service: FakeService) -> None:
    service.values[("sbio_cs = getconfigset(m);", 0)] = None
    service.values[("sbio_cs.StopTime", 1)] = 10.0
    service.values[("sbio_grid = linspace(0,10.0,100000)';", 0)] = None  # clamped, not 10_000_000
    service.values[("sbio_grid", 1)] = [[0.0], [10.0]]
    service.values[("sbio_run_1 = sbiosimulate(m);", 0)] = None
    service.values[("sbio_run_1_sel = selectbyname(sbio_run_1,{'A'});", 0)] = None
    service.values[("sbio_run_1_al = resample(sbio_run_1_sel,sbio_grid);", 0)] = None
    service.values[("sbio_run_1_al.DataNames", 1)] = "A"
    service.values[("sbio_run_1_al.Data", 1)] = [[1.0], [2.0]]

    with pytest.raises(ValueError):  # row-count mismatch (2 != clamped 100000) is incidental
        model.simulate_overlay_grid(runs=[{"label": "r", "species": ["A"]}], output_points=10_000_000)
    assert "sbio_grid = linspace(0,10.0,100000)';" in service.commands

