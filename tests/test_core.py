import pytest
from core.sbio_service import SbioService
from core.sbio_model import SbioModel
from engine.exceptions import (
    ProjectNotLoadedError, ModelNotFoundError, ElementNotFoundError)


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
