from pathlib import Path

import pytest
from core.sbio_service import SbioService
from core.sbio_model import SbioModel
from engine.exceptions import ProjectNotLoadedError, ModelNotFoundError, ElementNotFoundError

pytestmark = pytest.mark.matlab


def _loaded(project):
    svc = SbioService()
    svc.load_project(project)
    return svc


# --- SbioService ---
def test_load_returns_model_names(sample_project):
    assert SbioService().load_project(sample_project) == ["demo"]


def test_model_names_cached(sample_project):
    assert _loaded(sample_project).model_names() == ["demo"]


def test_get_model_single(sample_project):
    m = _loaded(sample_project).get_model()
    assert isinstance(m, SbioModel) and m.name == "demo"


def test_get_model_unknown_raises(sample_project):
    with pytest.raises(ModelNotFoundError):
        _loaded(sample_project).get_model("nope")


def test_get_model_before_load_raises():
    with pytest.raises(ProjectNotLoadedError):
        SbioService().get_model()


def test_save_before_load_raises():
    with pytest.raises(ProjectNotLoadedError):
        SbioService().save_project()


# --- SbioModel reads ---
def test_species_list(sample_project):
    assert _loaded(sample_project).get_model().species() == ["glucose", "lactate"]


def test_reactions_compartments_parameters(sample_project):
    m = _loaded(sample_project).get_model()
    assert m.reactions() == ["glycolysis"]
    assert m.compartments() == ["cell"]
    assert m.parameters() == ["k1"]


def test_get_species_detail(sample_project):
    m = _loaded(sample_project).get_model()
    assert m.get_species("glucose") == {"Name": "glucose", "Value": 10.0, "Units": "", "Compartment": "cell"}


def test_get_species_unknown_raises(sample_project):
    with pytest.raises(ElementNotFoundError):
        _loaded(sample_project).get_model().get_species("nope")


# --- SbioModel builders ---
def test_builder_returns_string_without_executing(sample_project):
    m = _loaded(sample_project).get_model()
    assert m.add_compartment_cmd("nucleus") == f"addcompartment({m.var},'nucleus');"
    assert m.compartments() == ["cell"]  # builder did not execute


def test_add_species_via_builder_and_persist(sample_project, tmp_path):
    svc = _loaded(sample_project)
    m = svc.get_model()
    svc.execute(m.add_species_cmd("cell", "atp", 5))
    assert "atp" in m.species()
    out = str(tmp_path / "out.sbproj")
    svc.save_project(out)
    reloaded = SbioService()
    reloaded.load_project(out)
    assert "atp" in reloaded.get_model().species()


def test_add_reaction_via_builder(sample_project):
    svc = _loaded(sample_project)
    m = svc.get_model()
    svc.execute(m.add_reaction_cmd("newrx", "glucose -> atp"))
    assert "newrx" in m.reactions()


def test_save_default_path_overwrites(sample_project, tmp_path):
    copy = str(tmp_path / "copy.sbproj")
    _loaded(sample_project).save_project(copy)  # make a copy at a new path
    svc = SbioService()
    svc.load_project(copy)
    svc.execute(svc.get_model().add_compartment_cmd("nucleus"))
    svc.save_project()  # no arg -> overwrites copy
    again = SbioService()
    again.load_project(copy)
    assert "nucleus" in again.get_model().compartments()


def test_save_project_creates_parent_directory(monkeypatch, tmp_path):
    svc = SbioService()
    target = tmp_path / "nested" / "project.sbproj"
    svc.project_path = str(target)
    svc._models = {"demo": "m"}

    def fake_execute(command, nargout=0):
        return None

    monkeypatch.setattr(svc, "execute", fake_execute)

    svc.save_project()

    assert target.parent.exists()


# --- error contract ---
def test_load_bad_path_raises(tmp_path):
    with pytest.raises(ProjectNotLoadedError):
        SbioService().load_project(str(tmp_path / "does_not_exist.sbproj"))


# --- detail variants ---
def test_get_reaction_detail(sample_project):
    m = _loaded(sample_project).get_model()
    assert m.get_reaction("glycolysis") == {"Name": "glycolysis", "Reaction": "glucose -> lactate", "Reversible": False}


def test_get_compartment_detail(sample_project):
    m = _loaded(sample_project).get_model()
    assert m.get_compartment("cell") == {"Name": "cell", "Capacity": 1.0, "Units": ""}


def test_get_parameter_detail(sample_project):
    m = _loaded(sample_project).get_model()
    assert m.get_parameter("k1") == {"Name": "k1", "Value": 1.5, "Units": ""}


def test_get_parameter_unknown_raises(sample_project):
    with pytest.raises(ElementNotFoundError):
        _loaded(sample_project).get_model().get_parameter("nope")


# --- doses and variants (getdose/getvariant path) ---
def test_doses_list(sample_project):
    assert _loaded(sample_project).get_model().doses() == ["d1"]


def test_variants_list(sample_project):
    assert _loaded(sample_project).get_model().variants() == ["v1"]


def test_get_dose_detail(sample_project):
    d = _loaded(sample_project).get_model().get_dose("d1")
    assert d["Name"] == "d1"
    assert d["Type"] == "repeat"
    assert d["TargetName"] == "glucose"
    assert d["Amount"] == 100.0


def test_get_dose_unknown_raises(sample_project):
    with pytest.raises(ElementNotFoundError):
        _loaded(sample_project).get_model().get_dose("nope")


def test_get_variant_detail(sample_project):
    v = _loaded(sample_project).get_model().get_variant("v1")
    assert v["Name"] == "v1"
    assert "Content" in v


def test_get_variant_unknown_raises(sample_project):
    with pytest.raises(ElementNotFoundError):
        _loaded(sample_project).get_model().get_variant("nope")


# --- dose/variant mutations, multi-entry, and schedule (real engine) ---
def test_schedule_dose_create_and_read(sample_project):
    svc = _loaded(sample_project)
    m = svc.get_model()
    svc.execute(m.add_dose_cmd("sched", "glucose", dose_type="schedule", times=[0, 5, 10], amounts=[10, 20, 30]))
    assert "sched" in m.doses()
    assert m.get_dose("sched")["Name"] == "sched"


def test_add_multi_entry_variant_executes(sample_project):
    svc = _loaded(sample_project)
    m = svc.get_model()
    svc.execute(
        m.add_variant_cmd(
            "v2",
            [
                {"type": "parameter", "name": "k1", "property": "Value", "value": 0.0},
                {"type": "species", "name": "glucose", "property": "InitialAmount", "value": 5.0},
            ],
        )
    )
    assert "v2" in m.variants()
    assert m.get_variant("v2")["Name"] == "v2"


def test_modify_dose_and_read(sample_project):
    svc = _loaded(sample_project)
    m = svc.get_model()
    svc.execute(m.set_dose_cmd("d1", amount=250))
    assert m.get_dose("d1")["Amount"] == 250.0


def test_modify_variant_replaces_content(sample_project):
    svc = _loaded(sample_project)
    m = svc.get_model()
    svc.execute(
        m.set_variant_cmd(
            "v1",
            [
                {"type": "parameter", "name": "k1", "property": "Value", "value": 9.0},
            ],
        )
    )
    assert "v1" in m.variants()


def test_remove_dose_and_variant(sample_project):
    svc = _loaded(sample_project)
    m = svc.get_model()
    svc.execute(m.delete_dose_cmd("d1"))
    assert "d1" not in m.doses()
    svc.execute(m.delete_variant_cmd("v1"))
    assert "v1" not in m.variants()


def test_simulate_with_dose_applies_bump(simulatable_project):
    svc = _loaded(simulatable_project)
    m = svc.get_model()
    svc.execute(m.set_configset_cmd(stop_time=10))
    svc.execute(m.add_dose_cmd("bolus", "A", dose_type="repeat", amount=100, start_time=5, interval=100, repeat_count=0))
    base = m.simulate()
    dosed = m.simulate(doses=["bolus"])
    assert max(dosed["data"]["A"]) > max(base["data"]["A"])


def test_simulate_with_variant_changes_rate(simulatable_project):
    svc = _loaded(simulatable_project)
    m = svc.get_model()
    svc.execute(m.set_configset_cmd(stop_time=10))
    svc.execute(m.add_variant_cmd("fast", [{"type": "parameter", "name": "k1", "property": "Value", "value": 5.0}]))
    base = m.simulate()
    fast = m.simulate(variants=["fast"])
    assert fast["data"]["A"][-1] < base["data"]["A"][-1]


def test_simulate_unknown_dose_raises(simulatable_project):
    with pytest.raises(ElementNotFoundError):
        _loaded(simulatable_project).get_model().simulate(doses=["nope"])


# --- schedule/infusion/content round-trips and multi-element arrays (real engine) ---
def _flatten(obj):
    """Recursively flatten nested MATLAB cell results (lists/tuples) to a flat list."""
    if isinstance(obj, (list, tuple)):
        out = []
        for item in obj:
            out.extend(_flatten(item))
        return out
    return [obj]


def test_schedule_dose_vectors_round_trip(sample_project):
    svc = _loaded(sample_project)
    m = svc.get_model()
    svc.execute(m.add_dose_cmd("sched", "glucose", dose_type="schedule", times=[0, 5, 10], amounts=[10, 20, 30]))
    d = m.get_dose("sched")
    assert d["Type"] == "schedule"
    assert d["TargetName"] == "glucose"
    # the numeric column vectors landed in MATLAB, in order
    svc.execute(f"sbio_probe = getdose({m.var},'sched');")
    assert svc.execute("sbio_probe.Time(1)", nargout=1) == 0.0
    assert svc.execute("sbio_probe.Time(3)", nargout=1) == 10.0
    assert svc.execute("sbio_probe.Amount(2)", nargout=1) == 20.0


def test_repeat_infusion_dose_round_trip(sample_project):
    # rate > 0 makes it a zero-order infusion rather than a bolus
    svc = _loaded(sample_project)
    m = svc.get_model()
    svc.execute(m.add_dose_cmd("inf", "glucose", dose_type="repeat", amount=50, rate=10, start_time=0))
    d = m.get_dose("inf")
    assert d["Type"] == "repeat"
    assert d["Amount"] == 50.0
    assert d["Rate"] == 10.0


def test_variant_content_round_trip(sample_project):
    v = _loaded(sample_project).get_model().get_variant("v1")
    assert v["Name"] == "v1"
    flat = _flatten(v["Content"])
    assert "parameter" in flat and "k1" in flat and "Value" in flat
    assert 3.0 in flat


def test_simulate_with_two_doses(simulatable_project):
    svc = _loaded(simulatable_project)
    m = svc.get_model()
    svc.execute(m.set_configset_cmd(stop_time=10))
    svc.execute(m.add_dose_cmd("b1", "A", dose_type="repeat", amount=100, start_time=2, interval=100, repeat_count=0))
    svc.execute(m.add_dose_cmd("b2", "A", dose_type="repeat", amount=100, start_time=6, interval=100, repeat_count=0))
    one = m.simulate(doses=["b1"])
    two = m.simulate(doses=["b1", "b2"])
    # a second bolus stacks on the decayed remainder of the first -> higher peak
    assert max(two["data"]["A"]) > max(one["data"]["A"])


def test_simulate_with_two_variants(simulatable_project):
    svc = _loaded(simulatable_project)
    m = svc.get_model()
    svc.execute(m.set_configset_cmd(stop_time=10))
    svc.execute(m.add_variant_cmd("hi_start", [{"type": "species", "name": "A", "property": "InitialAmount", "value": 20.0}]))
    svc.execute(m.add_variant_cmd("fast", [{"type": "parameter", "name": "k1", "property": "Value", "value": 5.0}]))
    start_only = m.simulate(variants=["hi_start"])
    both = m.simulate(variants=["hi_start", "fast"])
    assert start_only["data"]["A"][0] == 20.0  # species-InitialAmount variant applied
    assert both["data"]["A"][0] == 20.0  # first variant still applied within the array
    assert both["data"]["A"][-1] < start_only["data"]["A"][-1]  # second (fast k1) variant also applied


# --- export: plot reflects the run; CSV is real time-course (real engine) ---
def _parse_csv(text):
    lines = [line for line in text.splitlines() if line]
    header = lines[0].split(",")
    rows = [[float(cell) for cell in line.split(",")] for line in lines[1:]]
    return header, rows


def test_export_plot_writes_png(simulatable_project, tmp_path):
    svc = _loaded(simulatable_project)
    m = svc.get_model()
    svc.execute(m.set_configset_cmd(stop_time=10))
    out = tmp_path / "plot.png"
    result = m.export_plot(str(out))
    assert result == {"path": str(out), "resolution": 300}
    assert out.exists() and out.stat().st_size > 0


def test_export_plot_with_dose_writes_png(simulatable_project, tmp_path):
    svc = _loaded(simulatable_project)
    m = svc.get_model()
    svc.execute(m.set_configset_cmd(stop_time=10))
    svc.execute(m.add_dose_cmd("bolus", "A", dose_type="repeat", amount=100, start_time=5, interval=100, repeat_count=0))
    out = tmp_path / "dosed.png"
    m.export_plot(str(out), doses=["bolus"])  # must not crash and must honor the dose
    assert out.exists() and out.stat().st_size > 0


def test_export_csv_matches_simulate(simulatable_project):
    # CSV export is the real time-course: same values simulate() returns.
    from tools import sbio_tools

    svc = _loaded(simulatable_project)
    m = svc.get_model()
    svc.execute(m.set_configset_cmd(stop_time=10))
    sim = m.simulate()
    sbio_tools._service = svc
    out = Path(simulatable_project).with_name("sim_export.csv")
    try:
        csv_meta = sbio_tools.export_csv(path=str(out))
        csv_text = out.read_text()
    finally:
        sbio_tools._service = None
        out.unlink(missing_ok=True)
    header, rows = _parse_csv(csv_text)
    assert csv_meta["path"] == str(out)
    assert header == ["time", "A", "B"]
    assert len(rows) == len(sim["time"])
    assert rows[0][0] == sim["time"][0]
    assert rows[0][1] == sim["data"]["A"][0]  # A starts at 10
    assert rows[-1][1] < rows[0][1]  # A decays over the run


def test_export_csv_honors_dose(simulatable_project):
    from tools import sbio_tools

    svc = _loaded(simulatable_project)
    m = svc.get_model()
    svc.execute(m.set_configset_cmd(stop_time=10))
    svc.execute(m.add_dose_cmd("bolus", "A", dose_type="repeat", amount=100, start_time=5, interval=100, repeat_count=0))
    sbio_tools._service = svc
    base_out = Path(simulatable_project).with_name("base_export.csv")
    dosed_out = Path(simulatable_project).with_name("dosed_export.csv")
    try:
        sbio_tools.export_csv(path=str(base_out))
        sbio_tools.export_csv(path=str(dosed_out), doses=["bolus"])
        base = base_out.read_text()
        dosed = dosed_out.read_text()
    finally:
        sbio_tools._service = None
        base_out.unlink(missing_ok=True)
        dosed_out.unlink(missing_ok=True)
    base_max = max(row[1] for row in _parse_csv(base)[1])
    dosed_max = max(row[1] for row in _parse_csv(dosed)[1])
    assert dosed_max > base_max  # the dose shows up in the exported data


# --- multiple models ---
def test_get_model_ambiguous_raises(two_model_project):
    svc = SbioService()
    svc.load_project(two_model_project)
    with pytest.raises(ModelNotFoundError):
        svc.get_model()


def test_get_model_by_name_with_multiple(two_model_project):
    svc = SbioService()
    svc.load_project(two_model_project)
    assert svc.get_model("demo2").name == "demo2"
