"""End-to-end tests of the public MCP tools against a real MATLAB engine.

The unit tests in ``tests/unit/test_sbio_tools.py`` drive the ``@register`` tool
functions against a mocked ``DummyService`` (asserting the exact commands they
emit). These tests instead exercise the *same* tool functions through the real
``SbioService``/MATLAB engine â€” the actual path an MCP agent takes â€” so that
doses, variants, and simulation are validated end to end, not just at the
command-string layer.

``MatlabLayer`` is a singleton, so the tool module's lazily-created service
shares the one engine the session fixture already launched. Each test resets the
module-global service and rebuilds a fresh model via ``create_project`` (which
issues ``sbioreset``), keeping the tests independent of ordering.
"""

import math

import pytest

from simbiology_mcp.tools import sbio_tools

pytestmark = pytest.mark.matlab


@pytest.fixture(autouse=True)
def _fresh_tool_service():
    sbio_tools._service = None
    yield
    sbio_tools._service = None


def _build_decay_model():
    """Build the first-order decay model A -> B (rate k1*A) via the public tools."""
    sbio_tools.create_project("decay")
    sbio_tools.create_compartment("cell", "liter")
    sbio_tools.create_species("A", "cell", "mole", value=10.0)
    sbio_tools.create_species("B", "cell", "mole", value=0.0)
    sbio_tools.create_parameter("k1", 0.5, "1/second")
    sbio_tools.create_reaction("conversion", left="A", right="B", rate="k1*A")
    sbio_tools.configure_simulation(stop_time=10.0)


def test_tools_build_and_simulate():
    _build_decay_model()
    assert set(sbio_tools.list_species()) == {"A", "B"}
    result = sbio_tools.simulate_model()
    a, b = result["data"]["A"], result["data"]["B"]
    assert a[0] == 10.0 and b[0] == 0.0
    assert a[-1] < a[0]  # A decays
    assert b[-1] > b[0]  # B accumulates
    for ai, bi in zip(a, b):  # first-order decay conserves mass
        assert math.isclose(ai + bi, 10.0, rel_tol=1e-3, abs_tol=1e-6)


def test_tools_repeat_dose_end_to_end():
    _build_decay_model()
    sbio_tools.create_dose("bolus", "A", dose_type="repeat", amount=100.0, start_time=5.0, interval=100.0, repeat_count=0)
    assert sbio_tools.list_doses() == ["bolus"]

    base = sbio_tools.simulate_model()
    dosed = sbio_tools.simulate_model(doses=["bolus"])
    assert max(dosed["data"]["A"]) > max(base["data"]["A"])  # the bolus bumps A

    # a bigger bolus bumps A even higher, proving modify_dose reached the engine
    sbio_tools.modify_dose("bolus", amount=300.0)
    bigger = sbio_tools.simulate_model(doses=["bolus"])
    assert max(bigger["data"]["A"]) > max(dosed["data"]["A"])

    sbio_tools.remove_dose("bolus")
    assert sbio_tools.list_doses() == []


def test_tools_schedule_dose_end_to_end():
    _build_decay_model()
    sbio_tools.create_dose("sched", "A", dose_type="schedule", times=[0.0, 3.0, 6.0], amounts=[20.0, 20.0, 20.0])
    assert sbio_tools.list_doses() == ["sched"]

    base = sbio_tools.simulate_model()
    dosed = sbio_tools.simulate_model(doses=["sched"])
    assert set(dosed["data"]) == {"A", "B"}
    assert max(dosed["data"]["A"]) > max(base["data"]["A"])  # scheduled pulses raise A


def test_tools_variant_end_to_end():
    _build_decay_model()
    sbio_tools.create_variant("fast", [{"type": "parameter", "name": "k1", "property": "Value", "value": 5.0}])
    assert sbio_tools.list_variants() == ["fast"]

    base = sbio_tools.simulate_model()
    fast = sbio_tools.simulate_model(variants=["fast"])
    assert fast["data"]["A"][-1] < base["data"]["A"][-1]  # faster k1 -> more decay

    # slow it back down; modify_variant must reach the engine
    sbio_tools.modify_variant("fast", [{"type": "parameter", "name": "k1", "property": "Value", "value": 0.05}])
    slow = sbio_tools.simulate_model(variants=["fast"])
    assert slow["data"]["A"][-1] > fast["data"]["A"][-1]  # slower k1 -> less decay

    sbio_tools.remove_variant("fast")
    assert sbio_tools.list_variants() == []


def test_tools_multi_dose_and_variant():
    _build_decay_model()
    sbio_tools.create_dose("b1", "A", dose_type="repeat", amount=50.0, start_time=2.0, interval=100.0, repeat_count=0)
    sbio_tools.create_dose("b2", "A", dose_type="repeat", amount=50.0, start_time=6.0, interval=100.0, repeat_count=0)
    sbio_tools.create_variant("hi_start", [{"type": "species", "name": "A", "property": "InitialAmount", "value": 20.0}])
    sbio_tools.create_variant("fast", [{"type": "parameter", "name": "k1", "property": "Value", "value": 5.0}])

    result = sbio_tools.simulate_model(doses=["b1", "b2"], variants=["hi_start", "fast"])
    assert result["data"]["A"][0] == 20.0  # hi_start variant applied
    assert max(result["data"]["A"]) > 20.0  # at least one bolus stacked on top


def test_tools_export_graph_and_csv_end_to_end(tmp_path):
    _build_decay_model()
    sbio_tools.create_dose("bolus", "A", dose_type="repeat", amount=100.0, start_time=5.0, interval=100.0, repeat_count=0)

    # export_graph honors the dose and writes a real PNG
    out = tmp_path / "plot.png"
    assert sbio_tools.export_graph(
        path=str(out),
        doses=["bolus"],
        title="A and B over time",
        x_label="Time (second)",
        y_label="Amount (mole)",
        legend_labels=["Drug", "Metabolite"],
    ) == {"path": str(out), "resolution": 300}
    assert out.exists() and out.stat().st_size > 0

    # export_csv returns real time-course; the dose raises A's peak
    base_out = tmp_path / "base.csv"
    dosed_out = tmp_path / "dosed.csv"
    sbio_tools.export_csv(path=str(base_out))
    sbio_tools.export_csv(path=str(dosed_out), doses=["bolus"])
    header = base_out.read_text().splitlines()[0]
    assert header == "time,A,B"
    base_peak = max(float(r.split(",")[1]) for r in base_out.read_text().splitlines()[1:])
    dosed_peak = max(float(r.split(",")[1]) for r in dosed_out.read_text().splitlines()[1:])
    assert dosed_peak > base_peak

    # export_csv with a path writes a real file next to the PNG (same cwd base)
    csv_out = tmp_path / "data" / "run.csv"
    result = sbio_tools.export_csv(
        path=str(csv_out),
        doses=["bolus"],
        time_column="seconds",
        data_columns=["Drug", "Metabolite"],
        delimiter=";",
    )
    assert result["path"] == str(csv_out) and result["columns"] == ["seconds", "Drug", "Metabolite"]
    assert csv_out.exists() and csv_out.read_text().splitlines()[0] == "seconds;Drug;Metabolite"
    assert result["rows"] == len(csv_out.read_text().splitlines()) - 1

