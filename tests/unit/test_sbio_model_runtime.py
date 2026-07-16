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

