"""Pure unit tests for SbioModel command builders (no MATLAB engine).

The ``*_cmd`` builders only assemble MATLAB command strings; they never touch
the service, so they can be exercised with ``service=None`` and run anywhere
(including CI without MATLAB).
"""

from __future__ import annotations

import pytest

from core.sbio_model import (
    SbioModel,
    build_reaction_equation,
    _split_reaction_spec,
    to_matlab_number,
    to_matlab_string,
)


@pytest.fixture
def model() -> SbioModel:
    return SbioModel(service=None, var="m", name="demo")  # type: ignore[arg-type]


# --- value formatting ---
def test_to_matlab_string_escapes_quotes():
    assert to_matlab_string("a'b") == "'a''b'"
    assert to_matlab_string("plain") == "'plain'"


def test_to_matlab_number_is_float_literal():
    assert to_matlab_number(5) == "5.0"
    assert to_matlab_number(1.5) == "1.5"


def test_split_reaction_spec():
    assert _split_reaction_spec("a -> b") == ("a -> b", None)
    assert _split_reaction_spec("a -> b; k*a") == ("a -> b", "k*a")
    assert _split_reaction_spec("a -> b;   ") == ("a -> b", None)


# --- add builders ---
def test_add_species_cmd(model):
    assert model.add_species_cmd("cell", "atp", 5) == (
        "addspecies(sbioselect(m,'Type','compartment','Name','cell'),'atp',5.0);")


def test_add_compartment_cmd(model):
    assert model.add_compartment_cmd("nucleus") == "addcompartment(m,'nucleus');"


def test_add_parameter_cmd(model):
    assert model.add_parameter_cmd("k2", 2) == "addparameter(m,'k2',2.0);"


def test_add_reaction_cmd_without_rate(model):
    assert model.add_reaction_cmd("rx", "a -> b") == (
        "rxnObj = addreaction(m,'a -> b'); set(rxnObj,'Name','rx');")


def test_add_reaction_cmd_with_rate(model):
    assert model.add_reaction_cmd("rx", "a -> b; k * a") == (
        "rxnObj = addreaction(m,'a -> b'); set(rxnObj,'Name','rx'); "
        "rxnObj.ReactionRate = 'k * a';")


def test_add_reaction_cmd_with_numeric_rate(model):
    assert model.add_reaction_cmd("rx", "a -> b; 1") == (
        "rxnObj = addreaction(m,'a -> b'); set(rxnObj,'Name','rx'); "
        "rxnObj.ReactionRate = 1.0;")


def test_build_reaction_equation_structured():
    assert build_reaction_equation("mRNA_LacI", "LacI") == "mRNA_LacI -> LacI"
    assert build_reaction_equation("LuxR + AHL_in", "LuxR_AHL") == "LuxR + AHL_in -> LuxR_AHL"
    assert build_reaction_equation("null", "mRNA_LacI") == "null -> mRNA_LacI"
    assert build_reaction_equation("mRNA_LacI", "null") == "mRNA_LacI -> null"
    assert build_reaction_equation("A", "B", reversible=True) == "A <-> B"


# --- delete / rename builders ---
def test_delete_cmds(model):
    assert model.delete_species_cmd("glucose") == (
        "delete(sbioselect(m,'Type','species','Name','glucose'));")
    assert model.delete_reaction_cmd("rx") == (
        "delete(sbioselect(m,'Type','reaction','Name','rx'));")
    assert model.delete_model_cmd() == "delete(m);"


def test_rename_model_cmd(model):
    assert model.rename_model_cmd("renamed") == "m.Name = 'renamed';"


# --- set builders: field formatting per element type ---
def test_set_species_cmd(model):
    assert model.set_species_cmd("s", value=3, units="molarity") == (
        "sbio_e = sbioselect(m,'Type','species','Name','s'); "
        "sbio_e.Value = 3.0; sbio_e.InitialAmountUnits = 'molarity';")


def test_set_parameter_cmd(model):
    assert model.set_parameter_cmd("k1", value=2, units="1/second") == (
        "sbio_e = sbioselect(m,'Type','parameter','Name','k1'); "
        "sbio_e.Value = 2.0; sbio_e.ValueUnits = '1/second';")


def test_set_compartment_cmd(model):
    assert model.set_compartment_cmd("cell", capacity=2, units="liter") == (
        "sbio_e = sbioselect(m,'Type','compartment','Name','cell'); "
        "sbio_e.Capacity = 2.0; sbio_e.CapacityUnits = 'liter';")


def test_set_reaction_cmd_reversible_renders_boolean(model):
    assert model.set_reaction_cmd("rx", reaction="a -> c", reversible=True) == (
        "sbio_e = sbioselect(m,'Type','reaction','Name','rx'); "
        "sbio_e.Reaction = 'a -> c'; sbio_e.Reversible = true;")
    assert model.set_reaction_cmd("rx", reversible=False) == (
        "sbio_e = sbioselect(m,'Type','reaction','Name','rx'); "
        "sbio_e.Reversible = false;")


def test_set_cmd_rejects_unknown_field(model):
    with pytest.raises(KeyError):
        model.set_species_cmd("s", bogus=1)


# --- configset (simulation settings) builder ---
def test_set_configset_cmd_formats_string_and_numeric_fields(model):
    assert model.set_configset_cmd(stop_time=5, solver_type="ode45") == (
        "sbio_cs = getconfigset(m); "
        "sbio_cs.StopTime = 5.0; sbio_cs.SolverType = 'ode45';")


def test_set_configset_cmd_rejects_unknown_setting(model):
    with pytest.raises(KeyError):
        model.set_configset_cmd(nonsense=1)
