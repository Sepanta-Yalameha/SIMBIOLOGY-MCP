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


# --- dose builders (getdose/adddose path, not sbioselect) ---
def test_add_dose_cmd_repeat(model):
    assert model.add_dose_cmd(
        "d1", "drug", "repeat", amount=100, start_time=0, interval=8,
        repeat_count=5, rate=0, amount_units="milligram", time_units="hour") == (
        "sbio_d = adddose(m,'d1','repeat'); sbio_d.TargetName = 'drug'; "
        "sbio_d.Amount = 100.0; sbio_d.StartTime = 0.0; sbio_d.Interval = 8.0; "
        "sbio_d.RepeatCount = 5.0; sbio_d.Rate = 0.0; "
        "sbio_d.AmountUnits = 'milligram'; sbio_d.TimeUnits = 'hour';")


def test_add_dose_cmd_schedule(model):
    assert model.add_dose_cmd(
        "d2", "drug", "schedule", times=[0, 8, 16], amounts=[100, 50, 50],
        rates=[0, 0, 0], amount_units="milligram") == (
        "sbio_d = adddose(m,'d2','schedule'); sbio_d.TargetName = 'drug'; "
        "sbio_d.Time = [0.0;8.0;16.0]; sbio_d.Amount = [100.0;50.0;50.0]; "
        "sbio_d.Rate = [0.0;0.0;0.0]; sbio_d.AmountUnits = 'milligram';")


def test_set_dose_cmd(model):
    assert model.set_dose_cmd("d1", amount=200, target="drug2", amount_units="gram") == (
        "sbio_e = getdose(m,'d1'); sbio_e.Amount = 200.0; "
        "sbio_e.TargetName = 'drug2'; sbio_e.AmountUnits = 'gram';")


def test_set_dose_cmd_rejects_unknown_field(model):
    with pytest.raises(KeyError):
        model.set_dose_cmd("d1", bogus=1)


def test_delete_dose_cmd(model):
    assert model.delete_dose_cmd("d1") == "rmdose(m,'d1');"


# --- variant builders (getvariant/addvariant path, not sbioselect) ---
def test_add_variant_cmd_multi_entry(model):
    assert model.add_variant_cmd("v1", [
        {"type": "parameter", "name": "k1", "property": "Value", "value": 0},
        {"type": "species", "name": "A", "property": "InitialAmount", "value": 5},
    ]) == (
        "sbio_v = addvariant(m,'v1'); "
        "addcontent(sbio_v,{{'parameter','k1','Value',0.0},{'species','A','InitialAmount',5.0}});")


def test_add_variant_cmd_no_content(model):
    assert model.add_variant_cmd("v2", []) == "sbio_v = addvariant(m,'v2');"


def test_set_variant_cmd(model):
    assert model.set_variant_cmd("v1", [
        {"type": "parameter", "name": "k1", "property": "Value", "value": 0.5},
    ]) == (
        "sbio_e = getvariant(m,'v1'); "
        "sbio_e.Content = {{'parameter','k1','Value',0.5}};")


def test_delete_variant_cmd(model):
    assert model.delete_variant_cmd("v1") == "delete(getvariant(m,'v1'));"


def test_add_dose_cmd_rejects_mismatched_fields(model):
    with pytest.raises(ValueError):
        model.add_dose_cmd("d1", "drug", "schedule", repeat_count=3)
    with pytest.raises(ValueError):
        model.add_dose_cmd("d1", "drug", "repeat", times=[0, 1])
    # scalar amount/rate belong to a repeat dose, not a schedule dose
    with pytest.raises(ValueError):
        model.add_dose_cmd("d1", "drug", "schedule", amount=5, times=[0])
    # schedule vectors must line up
    with pytest.raises(ValueError):
        model.add_dose_cmd("d1", "drug", "schedule", times=[0, 8], amounts=[5])


def test_add_dose_cmd_rejects_unknown_dose_type(model):
    with pytest.raises(ValueError):
        model.add_dose_cmd("d1", "drug", "oral", amount=5)


def test_add_variant_cmd_rejects_incomplete_entry(model):
    with pytest.raises(ValueError):
        model.add_variant_cmd("v", [{"type": "parameter", "name": "k1", "value": 0}])


def test_variant_value_bool_renders_numeric(model):
    assert model.add_variant_cmd("v", [
        {"type": "parameter", "name": "on", "property": "Value", "value": True},
    ]) == "sbio_v = addvariant(m,'v'); addcontent(sbio_v,{{'parameter','on','Value',1.0}});"


# --- configset (simulation settings) builder ---
def test_set_configset_cmd_formats_string_and_numeric_fields(model):
    assert model.set_configset_cmd(stop_time=5, solver_type="ode45") == (
        "sbio_cs = getconfigset(m); "
        "sbio_cs.StopTime = 5.0; sbio_cs.SolverType = 'ode45';")


def test_set_configset_cmd_rejects_unknown_setting(model):
    with pytest.raises(KeyError):
        model.set_configset_cmd(nonsense=1)
