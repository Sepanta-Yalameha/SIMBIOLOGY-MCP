"""Unit tests for export tools that only verify MATLAB command sequencing."""

from __future__ import annotations

import sys
import types

sys.modules.setdefault("igem_registry_api", types.SimpleNamespace(Client=object))

import tools.sbio_tools as sbio_tools


class DummyModel:
    def __init__(self) -> None:
        self.var = "m"


class DummyService:
    def __init__(self) -> None:
        self.commands: list[str] = []
        self.model = DummyModel()

    def get_model(self, name=None):  # noqa: ANN001
        return self.model

    def execute(self, command: str, nargout: int = 0):  # noqa: ANN001
        self.commands.append(command)
        return None


def test_export_graph_uses_matlab_plot_and_export(monkeypatch):
    svc = DummyService()
    monkeypatch.setattr(sbio_tools, "_service", svc)

    result = sbio_tools.export_graph(path="out.png", resolution=600)

    assert result == {"path": "out.png", "resolution": 600}
    assert svc.commands == [
        "sim_data = sbiosimulate(m);",
        "axes_handle = sbioplot(sim_data);",
        "fig_handle = get(axes_handle, 'Parent');",
        "exportgraphics(fig_handle, 'out.png', 'Resolution', 600);",
    ]


def test_export_csv_returns_inventory(monkeypatch):
    svc = DummyService()
    monkeypatch.setattr(sbio_tools, "_model", lambda name=None: svc.model)
    svc.model.species = lambda: ["s1", "s2"]  # type: ignore[attr-defined]
    svc.model.reactions = lambda: ["r1"]  # type: ignore[attr-defined]
    svc.model.compartments = lambda: ["c1"]  # type: ignore[attr-defined]
    svc.model.parameters = lambda: ["k1"]  # type: ignore[attr-defined]

    result = sbio_tools.export_csv()

    assert result["csv"].splitlines() == [
        "kind,name",
        "species,s1",
        "species,s2",
        "reaction,r1",
        "compartment,c1",
        "parameter,k1",
    ]
