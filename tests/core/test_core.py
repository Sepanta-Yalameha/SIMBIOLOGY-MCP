import pytest
from core.sbio_service import SbioService
from core.sbio_model import SbioModel
from engine.exceptions import (
    ProjectNotLoadedError, ModelNotFoundError, ElementNotFoundError)

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
    assert m.get_species("glucose") == {
        "Name": "glucose", "Value": 10.0, "Units": "", "Compartment": "cell"}

def test_get_species_unknown_raises(sample_project):
    with pytest.raises(ElementNotFoundError):
        _loaded(sample_project).get_model().get_species("nope")


# --- SbioModel builders ---
def test_builder_returns_string_without_executing(sample_project):
    m = _loaded(sample_project).get_model()
    assert m.add_compartment_cmd("nucleus") == f"addcompartment({m.var},'nucleus');"
    assert m.compartments() == ["cell"]   # builder did not execute

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
    _loaded(sample_project).save_project(copy)        # make a copy at a new path
    svc = SbioService()
    svc.load_project(copy)
    svc.execute(svc.get_model().add_compartment_cmd("nucleus"))
    svc.save_project()                                # no arg -> overwrites copy
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
    assert m.get_reaction("glycolysis") == {
        "Name": "glycolysis", "Reaction": "glucose -> lactate", "Reversible": False}

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
