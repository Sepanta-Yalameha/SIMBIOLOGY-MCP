"""Unit tests for the export tools (hermetic; no MATLAB engine).

The export tools delegate simulation to ``SbioModel`` (``export_plot`` and
``simulate``); these tests use a dummy model to verify the tool-layer contract:
that the doses/variants/species arguments pass through and that ``export_csv``
formats a time-course into CSV. The real MATLAB plotting/simulation path is
covered by the ``matlab``-marked tests.
"""

from __future__ import annotations

import tools.sbio_tools as sbio_tools


class DummyModel:
    """Records export_plot/simulate calls and returns a canned time-course."""

    def __init__(self) -> None:
        self.plot_calls: list[dict] = []
        self.simulate_calls: list[dict] = []

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
