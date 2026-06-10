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


# --- builder string formats (pure, no execution) ---
def test_builder_string_formats(sample_project):
    m = _loaded(sample_project).get_model()
    assert m.add_species_cmd("cell", "atp", 5) == (
        f"addspecies(sbioselect({m.var},'Type','compartment','Name','cell'),'atp',5.0);")
    assert m.add_parameter_cmd("k2", 2) == f"addparameter({m.var},'k2',2.0);"
    assert m.add_reaction_cmd("rx", "a -> b") == (
        f"rxnObj = addreaction({m.var},'a -> b'); set(rxnObj,'Name','rx');")
    assert m.add_reaction_cmd("rx", "lac_dna -> lac_dna + lac_mrna; k_tx * lac_dna") == (
        f"rxnObj = addreaction({m.var},'lac_dna -> lac_dna + lac_mrna'); set(rxnObj,'Name','rx'); "
        "rxnObj.ReactionRate = 'k_tx * lac_dna';")

def test_delete_and_modify_builder_formats(sample_project):
    m = _loaded(sample_project).get_model()
    assert m.delete_species_cmd("glucose") == (
        f"delete(sbioselect({m.var},'Type','species','Name','glucose'));")
    assert m.set_parameter_cmd("k1", value=2, units="1/second") == (
        f"sbio_e = sbioselect({m.var},'Type','parameter','Name','k1'); "
        "sbio_e.Value = 2.0; sbio_e.ValueUnits = '1/second';")
    assert m.rename_model_cmd("renamed") == f"{m.var}.Name = 'renamed';"

def test_to_matlab_string_escapes():
    from core.sbio_model import to_matlab_string
    assert to_matlab_string("a'b") == "'a''b'"


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
