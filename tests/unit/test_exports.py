"""Unit tests for the export tools (hermetic; no MATLAB engine).

The export tools delegate simulation to ``SbioModel`` (``export_plot`` and
``simulate``); these tests use a dummy model to verify the tool-layer contract:
that the doses/variants/species arguments pass through and that ``export_csv``
formats a time-course into CSV. The real MATLAB plotting/simulation path is
covered by the ``matlab``-marked tests.
"""

from __future__ import annotations

import pytest

import simbiology_mcp.tools.sbio_tools as sbio_tools


class DummyModel:
    """Records export_plot/simulate calls and returns a canned time-course."""

    def __init__(self) -> None:
        self.plot_calls: list[dict] = []
        self.simulate_calls: list[dict] = []
        self.overlay_plot_calls: list[dict] = []
        self.overlay_grid_calls: list[dict] = []

    def export_plot(
        self,
        path,
        resolution=300,
        species=None,
        doses=None,
        variants=None,
        title=None,
        x_label=None,
        y_label=None,
        legend_labels=None,
    ):
        self.plot_calls.append(
            {
                "path": path,
                "resolution": resolution,
                "species": species,
                "doses": doses,
                "variants": variants,
                "title": title,
                "x_label": x_label,
                "y_label": y_label,
                "legend_labels": legend_labels,
            }
        )
        return {"path": path, "resolution": resolution}

    def simulate(self, species=None, doses=None, variants=None):
        self.simulate_calls.append({"species": species, "doses": doses, "variants": variants})
        return {
            "time": [0.0, 1.0, 2.0],
            "time_units": "second",
            "names": ["A", "B"],
            "data": {"A": [10.0, 6.0, 3.0], "B": [0.0, 4.0, 7.0]},
        }

    def export_overlay_plot(self, path, runs, resolution=300, species=None, title=None, x_label=None, y_label=None, legend_labels=None):
        self.overlay_plot_calls.append(
            {
                "path": path,
                "runs": runs,
                "resolution": resolution,
                "species": species,
                "title": title,
                "x_label": x_label,
                "y_label": y_label,
                "legend_labels": legend_labels,
            }
        )
        labels = [run["label"] for run in runs]
        return {"path": path, "resolution": resolution, "runs": labels}

    def simulate_overlay_grid(self, runs, species=None, output_points=200):
        self.overlay_grid_calls.append({"runs": runs, "species": species, "output_points": output_points})
        labels = [run["label"] for run in runs]
        return {
            "time": [0.0, 5.0, 10.0],
            "time_units": "second",
            "columns": [(label, [float(i), float(i) + 1.0, float(i) + 2.0]) for i, label in enumerate(labels)],
            "labels": labels,
        }


def _install(monkeypatch) -> DummyModel:
    model = DummyModel()
    monkeypatch.setattr(sbio_tools, "_model", lambda name=None: model)
    return model


def test_export_graph_delegates_to_export_plot(monkeypatch):
    model = _install(monkeypatch)

    result = sbio_tools.export_graph(
        path="out.png",
        resolution=600,
        species=["A"],
        doses=["d1"],
        variants=["v1"],
        title="ATP over time",
        x_label="Time (s)",
        y_label="Concentration (mM)",
        legend_labels=["ATP"],
    )

    assert result == {"path": "out.png", "resolution": 600}
    assert model.plot_calls == [
        {
            "path": "out.png",
            "resolution": 600,
            "species": ["A"],
            "doses": ["d1"],
            "variants": ["v1"],
            "title": "ATP over time",
            "x_label": "Time (s)",
            "y_label": "Concentration (mM)",
            "legend_labels": ["ATP"],
        }
    ]


def test_export_graph_default_path(monkeypatch):
    model = _install(monkeypatch)

    result = sbio_tools.export_graph()

    assert result["path"] == "simbiology_plot.png"
    assert model.plot_calls[0]["path"] == "simbiology_plot.png"
    assert model.plot_calls[0]["doses"] is None


def test_export_csv_writes_timecourse_to_path(monkeypatch, tmp_path):
    _install(monkeypatch)
    out = tmp_path / "out.csv"

    result = sbio_tools.export_csv(path=str(out))

    assert result == {"path": str(out), "rows": 3, "columns": ["time", "A", "B"]}
    assert out.read_text().splitlines() == [
        "time,A,B",
        "0.0,10.0,0.0",
        "1.0,6.0,4.0",
        "2.0,3.0,7.0",
    ]


def test_export_csv_passes_through_doses_variants_species(monkeypatch):
    model = _install(monkeypatch)

    sbio_tools.export_csv(path="out.csv", species=["A"], doses=["d1"], variants=["v1"])

    assert model.simulate_calls == [{"species": ["A"], "doses": ["d1"], "variants": ["v1"]}]


def test_export_csv_supports_custom_headers_and_delimiter(monkeypatch, tmp_path):
    _install(monkeypatch)
    out = tmp_path / "custom.csv"

    result = sbio_tools.export_csv(
        path=str(out),
        time_column="minutes",
        data_columns=["Drug", "Metabolite"],
        delimiter=";",
    )

    assert result == {"path": str(out), "rows": 3, "columns": ["minutes", "Drug", "Metabolite"]}
    assert out.read_text().splitlines() == [
        "minutes;Drug;Metabolite",
        "0.0;10.0;0.0",
        "1.0;6.0;4.0",
        "2.0;3.0;7.0",
    ]


def test_export_csv_writes_file_when_path_given(tmp_path, monkeypatch):
    _install(monkeypatch)
    out = tmp_path / "nested" / "out.csv"  # parent dir must be created

    result = sbio_tools.export_csv(path=str(out))

    assert result == {"path": str(out), "rows": 3, "columns": ["time", "A", "B"]}
    assert out.read_text().splitlines() == [
        "time,A,B",
        "0.0,10.0,0.0",
        "1.0,6.0,4.0",
        "2.0,3.0,7.0",
    ]


def test_export_csv_rejects_bad_header_lengths(monkeypatch):
    _install(monkeypatch)

    try:
        sbio_tools.export_csv(path="out.csv", data_columns=["only_one"])
    except ValueError as exc:
        assert "data_columns" in str(exc)
    else:
        raise AssertionError("expected ValueError for mismatched data_columns")


# --- multi-run overlays ---
def test_export_graph_with_runs_delegates_to_overlay_plot(monkeypatch):
    model = _install(monkeypatch)

    result = sbio_tools.export_graph(
        path="overlay.png",
        species=["GFP"],
        title="GFP by arsenic level",
        runs=[{"label": "low", "variants": ["arsenic_low"]}, {"label": "high", "variants": ["arsenic_high"]}],
    )

    assert result == {"path": "overlay.png", "resolution": 300, "runs": ["low", "high"]}
    assert model.plot_calls == []  # single-run path untouched
    assert model.overlay_plot_calls == [
        {
            "path": "overlay.png",
            "runs": [{"label": "low", "variants": ["arsenic_low"]}, {"label": "high", "variants": ["arsenic_high"]}],
            "resolution": 300,
            "species": ["GFP"],
            "title": "GFP by arsenic level",
            "x_label": None,
            "y_label": None,
            "legend_labels": None,
        }
    ]


def test_export_csv_with_runs_writes_wide_csv(monkeypatch, tmp_path):
    model = _install(monkeypatch)
    out = tmp_path / "overlay.csv"

    result = sbio_tools.export_csv(
        path=str(out),
        species=["GFP"],
        runs=[{"label": "low", "variants": ["arsenic_low"]}, {"label": "high", "variants": ["arsenic_high"]}],
        output_points=3,
    )

    assert model.simulate_calls == []  # single-run path untouched
    assert model.overlay_grid_calls == [
        {"runs": [{"label": "low", "variants": ["arsenic_low"]}, {"label": "high", "variants": ["arsenic_high"]}], "species": ["GFP"], "output_points": 3}
    ]
    # one shared time column plus one column per run, equal row counts
    assert result == {"path": str(out), "rows": 3, "columns": ["time", "low", "high"], "runs": ["low", "high"]}
    assert out.read_text().splitlines() == [
        "time,low,high",
        "0.0,0.0,1.0",
        "5.0,1.0,2.0",
        "10.0,2.0,3.0",
    ]


def test_export_csv_with_runs_rejects_time_column_collision(monkeypatch, tmp_path):
    _install(monkeypatch)
    out = tmp_path / "overlay.csv"

    # a run named "time" would collide with the prepended time column
    with pytest.raises(ValueError, match="collides with the time column"):
        sbio_tools.export_csv(path=str(out), runs=[{"label": "time"}], species=["GFP"])
    assert not out.exists()


def test_export_csv_with_runs_rejects_data_columns(monkeypatch, tmp_path):
    model = _install(monkeypatch)
    out = tmp_path / "overlay.csv"

    with pytest.raises(ValueError, match="data_columns is not supported with runs"):
        sbio_tools.export_csv(path=str(out), runs=[{"label": "low"}], data_columns=["x"])
    assert model.overlay_grid_calls == []  # rejected before simulating
    assert not out.exists()

