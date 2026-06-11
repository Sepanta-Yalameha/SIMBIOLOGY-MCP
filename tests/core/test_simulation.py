import math

import pytest

from core.sbio_service import SbioService

pytestmark = pytest.mark.matlab


def _loaded(project):
    svc = SbioService()
    svc.load_project(project)
    return svc


# --- configset builder (pure string, no execution) ---
def test_set_configset_cmd_format(simulatable_project):
    m = _loaded(simulatable_project).get_model()
    assert m.set_configset_cmd(stop_time=5, solver_type="ode45") == (
        f"sbio_cs = getconfigset({m.var}); "
        "sbio_cs.StopTime = 5.0; sbio_cs.SolverType = 'ode45';")


def test_set_configset_cmd_unknown_field_raises(simulatable_project):
    m = _loaded(simulatable_project).get_model()
    try:
        m.set_configset_cmd(nonsense=1)
    except KeyError:
        return
    raise AssertionError("expected KeyError for unsupported setting")


# --- configset reads ---
def test_default_settings(simulatable_project):
    cfg = _loaded(simulatable_project).get_model().get_configset()
    assert cfg["StopTime"] == 10.0
    assert cfg["SolverType"] == "ode15s"
    # Inf defaults are collapsed to None for JSON safety.
    assert cfg["MaximumWallClock"] is None
    assert cfg["MaximumNumberOfLogs"] is None


def test_configure_then_read(simulatable_project):
    svc = _loaded(simulatable_project)
    m = svc.get_model()
    svc.execute(m.set_configset_cmd(
        stop_time=5, solver_type="ode45", absolute_tolerance=1e-7))
    cfg = m.get_configset()
    assert cfg["StopTime"] == 5.0
    assert cfg["SolverType"] == "ode45"
    assert math.isclose(cfg["AbsoluteTolerance"], 1e-7, rel_tol=1e-9)


def test_stochastic_solver_settings_readable(simulatable_project):
    # ssa uses SSASolverOptions, which has no tolerances; reading settings
    # must not crash and must simply omit the tolerance keys.
    svc = _loaded(simulatable_project)
    m = svc.get_model()
    svc.execute(m.set_configset_cmd(solver_type="ssa"))
    cfg = m.get_configset()
    assert cfg["SolverType"] == "ssa"
    assert "AbsoluteTolerance" not in cfg
    assert "RelativeTolerance" not in cfg


# --- running a simulation ---
def test_simulate_returns_timecourse(simulatable_project):
    svc = _loaded(simulatable_project)
    m = svc.get_model()
    svc.execute(m.set_configset_cmd(stop_time=10))
    result = m.simulate()

    assert set(result["data"]) == {"A", "B"}
    assert result["time"][0] == 0.0
    assert math.isclose(result["time"][-1], 10.0, rel_tol=1e-6)

    a, b = result["data"]["A"], result["data"]["B"]
    assert a[0] == 10.0 and b[0] == 0.0
    assert a[-1] < a[0]            # A decays
    assert b[-1] > b[0]            # B accumulates
    # first-order decay conserves mass: A + B == 10 at every step
    for ai, bi in zip(a, b):
        assert math.isclose(ai + bi, 10.0, rel_tol=1e-3, abs_tol=1e-6)


def test_simulate_species_filter(simulatable_project):
    svc = _loaded(simulatable_project)
    m = svc.get_model()
    result = m.simulate(species=["B"])
    assert list(result["data"]) == ["B"]
    assert result["names"] == ["B"]
    assert len(result["data"]["B"]) == len(result["time"])
