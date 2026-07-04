"""Unit tests for the public SimBiology MCP tools."""

from __future__ import annotations

import asyncio
import sys
import types

import pytest

sys.modules.setdefault("igem_registry_api", types.SimpleNamespace(Client=object))

from tools import sbio_tools
from tools.registry import TOOLS

try:
    from interfaces.mcp_server import build_server
except ModuleNotFoundError:
    build_server = None

SBIO_TOOL_NAMES = {
    "load_project",
    "create_project",
    "save_project",
    "create_model",
    "rename_model",
    "remove_model",
    "list_models",
    "list_species",
    "list_reactions",
    "list_compartments",
    "list_parameters",
    "create_compartment",
    "modify_compartment",
    "remove_compartment",
    "create_species",
    "modify_species",
    "remove_species",
    "create_reaction",
    "modify_reaction",
    "remove_reaction",
    "create_parameter",
    "modify_parameter",
    "remove_parameter",
    "get_simulation_settings",
    "configure_simulation",
    "simulate_model",
    "export_graph",
    "export_csv",
    "create_dose",
    "modify_dose",
    "remove_dose",
    "list_doses",
    "create_variant",
    "modify_variant",
    "remove_variant",
    "list_variants",
}


class DummyModel:
    def __init__(self, name: str = "demo", var: str = "m") -> None:
        self.name = name
        self.var = var

    def species(self) -> list[str]:
        return ["S1", "S2"]

    def reactions(self) -> list[str]:
        return ["R1"]

    def compartments(self) -> list[str]:
        return ["cell"]

    def parameters(self) -> list[str]:
        return ["k1"]

    def get_configset(self) -> dict[str, object]:
        return {"StopTime": 10.0, "SolverType": "ode15s"}

    def simulate(
        self,
        species: list[str] | None = None,
        doses: list[str] | None = None,
        variants: list[str] | None = None,
    ) -> dict[str, object]:
        names = species or ["S1", "S2"]
        return {"time": [0.0, 1.0], "names": names, "data": {name: [1.0, 0.5] for name in names}}

    def add_compartment_cmd(self, name: str) -> str:
        return f"add_compartment:{name}"

    def set_compartment_cmd(self, name: str, **fields: object) -> str:
        return f"set_compartment:{name}:{fields!r}"

    def delete_compartment_cmd(self, name: str) -> str:
        return f"delete_compartment:{name}"

    def add_species_cmd(self, compartment: str, name: str, value: float) -> str:
        return f"add_species:{compartment}:{name}:{value}"

    def set_species_cmd(self, name: str, **fields: object) -> str:
        return f"set_species:{name}:{fields!r}"

    def delete_species_cmd(self, name: str) -> str:
        return f"delete_species:{name}"

    def add_reaction_cmd(self, name: str, equation: str) -> str:
        return f"add_reaction:{name}:{equation}"

    def set_reaction_cmd(self, name: str, **fields: object) -> str:
        return f"set_reaction:{name}:{fields!r}"

    def delete_reaction_cmd(self, name: str) -> str:
        return f"delete_reaction:{name}"

    def add_parameter_cmd(self, name: str, value: float) -> str:
        return f"add_parameter:{name}:{value}"

    def set_parameter_cmd(self, name: str, **fields: object) -> str:
        return f"set_parameter:{name}:{fields!r}"

    def delete_parameter_cmd(self, name: str) -> str:
        return f"delete_parameter:{name}"

    def set_configset_cmd(self, **fields: object) -> str:
        return f"set_configset:{fields!r}"

    def doses(self) -> list[str]:
        return ["d1"]

    def add_dose_cmd(self, name: str, target: str, **fields: object) -> str:
        return f"add_dose:{name}:{target}:{fields!r}"

    def set_dose_cmd(self, name: str, **fields: object) -> str:
        return f"set_dose:{name}:{fields!r}"

    def delete_dose_cmd(self, name: str) -> str:
        return f"delete_dose:{name}"

    def variants(self) -> list[str]:
        return ["v1"]

    def add_variant_cmd(self, name: str, content: list) -> str:
        return f"add_variant:{name}:{content!r}"

    def set_variant_cmd(self, name: str, content: list) -> str:
        return f"set_variant:{name}:{content!r}"

    def delete_variant_cmd(self, name: str) -> str:
        return f"delete_variant:{name}"


class DummyService:
    def __init__(self) -> None:
        self.project_path = "demo.sbproj"
        self.commands: list[str] = []
        self.model = DummyModel()

    def load_project(self, path: str) -> list[str]:
        self.project_path = path
        return [self.model.name]

    def create_project(self, model_name: str, path: str | None = None) -> list[str]:
        self.project_path = path or f"{model_name}.sbproj"
        self.model = DummyModel(name=model_name)
        return [model_name]

    def save_project(self, path: str | None = None) -> None:
        if path is not None:
            self.project_path = path

    def create_model(self, name: str) -> DummyModel:
        self.model = DummyModel(name=name)
        return self.model

    def rename_model(self, old_name: str, new_name: str) -> DummyModel:
        assert old_name == self.model.name
        self.model.name = new_name
        return self.model

    def delete_model(self, name: str) -> None:
        self.commands.append(f"delete_model:{name}")

    def model_names(self) -> list[str]:
        return [self.model.name]

    def get_model(self, name: str | None = None) -> DummyModel:
        if name is not None:
            assert name == self.model.name
        return self.model

    def execute(self, command: str, nargout: int = 0) -> None:
        self.commands.append(command)


@pytest.fixture(autouse=True)
def reset_service():
    sbio_tools._service = None
    yield
    sbio_tools._service = None


@pytest.fixture
def svc(monkeypatch: pytest.MonkeyPatch) -> DummyService:
    service = DummyService()
    monkeypatch.setattr(sbio_tools, "_service", service)
    return service


def test_sbio_tools_are_registered() -> None:
    assert SBIO_TOOL_NAMES <= set(TOOLS)
    assert {name for name in SBIO_TOOL_NAMES if TOOLS[name].__module__ == "tools.sbio_tools"} == SBIO_TOOL_NAMES


def test_build_server_lists_sbio_tools() -> None:
    if build_server is None:
        pytest.skip("FastMCP import not available in this interpreter")
    names = {tool.name for tool in asyncio.run(build_server().list_tools(run_middleware=False))}
    assert SBIO_TOOL_NAMES <= names


def test_project_and_model_tools(svc: DummyService) -> None:
    assert sbio_tools.load_project("loaded.sbproj") == {
        "project_path": "loaded.sbproj",
        "models": ["demo"],
    }
    assert sbio_tools.create_project("fresh", path="fresh.sbproj") == {
        "project_path": "fresh.sbproj",
        "models": ["fresh"],
    }
    assert sbio_tools.save_project() == {"project_path": "fresh.sbproj"}
    assert sbio_tools.create_model("renameme") == {"name": "renameme"}
    assert sbio_tools.rename_model("renameme", "renamed") == {"name": "renamed"}
    assert sbio_tools.remove_model("renamed") == {"removed": "renamed"}
    assert sbio_tools.list_models() == ["renamed"]
    assert "delete_model:renamed" in svc.commands


def test_read_tools(svc: DummyService) -> None:
    assert sbio_tools.list_species() == ["S1", "S2"]
    assert sbio_tools.list_reactions() == ["R1"]
    assert sbio_tools.list_compartments() == ["cell"]
    assert sbio_tools.list_parameters() == ["k1"]


def test_structure_tools_issue_expected_commands(svc: DummyService) -> None:
    assert sbio_tools.create_compartment("nucleus", capacity=2.0) == {"name": "nucleus", "capacity": 2.0}
    assert sbio_tools.modify_compartment("nucleus", capacity=3.0, units="liter") == {
        "name": "nucleus",
        "capacity": 3.0,
        "units": "liter",
    }
    assert sbio_tools.remove_compartment("nucleus") == {"removed": "nucleus"}

    assert sbio_tools.create_species("ATP", "cell", value=5.0) == {
        "name": "ATP",
        "compartment": "cell",
        "value": 5.0,
    }
    assert sbio_tools.modify_species("ATP", value=6.0, units="molarity") == {
        "name": "ATP",
        "value": 6.0,
        "units": "molarity",
    }
    assert sbio_tools.remove_species("ATP") == {"removed": "ATP"}

    assert sbio_tools.create_reaction("rx1", left="A", right="B", reversible=True, rate="k*A") == {
        "name": "rx1",
        "left": "A",
        "right": "B",
        "reversible": True,
        "rate": "k*A",
    }
    assert sbio_tools.modify_reaction("rx1", left="B", right="C", reversible=False, rate="k2*B") == {
        "name": "rx1",
        "reaction": "B -> C",
        "reversible": False,
        "rate": "k2*B",
    }
    assert sbio_tools.remove_reaction("rx1") == {"removed": "rx1"}

    assert sbio_tools.create_parameter("k1", 1.5) == {"name": "k1", "value": 1.5}
    assert sbio_tools.modify_parameter("k1", value=2.0, units="1/second") == {
        "name": "k1",
        "value": 2.0,
        "units": "1/second",
    }
    assert sbio_tools.remove_parameter("k1") == {"removed": "k1"}

    assert svc.commands == [
        "add_compartment:nucleus",
        "set_compartment:nucleus:{'capacity': 2.0}",
        "set_compartment:nucleus:{'capacity': 3.0, 'units': 'liter'}",
        "delete_compartment:nucleus",
        "add_species:cell:ATP:5.0",
        "set_species:ATP:{'value': 6.0, 'units': 'molarity'}",
        "delete_species:ATP",
        "add_reaction:rx1:A <-> B; k*A",
        "set_reaction:rx1:{'reaction': 'B -> C', 'reversible': False, 'rate': 'k2*B'}",
        "delete_reaction:rx1",
        "add_parameter:k1:1.5",
        "set_parameter:k1:{'value': 2.0, 'units': '1/second'}",
        "delete_parameter:k1",
    ]


def test_modify_reaction_partial_edit_keeps_stoichiometry(svc: DummyService) -> None:
    # Regression: left/right default to "", so modify_reaction used to always
    # rewrite the equation, wiping the stoichiometry to " -> " when a caller
    # changed only the rate or reversibility.
    assert sbio_tools.modify_reaction("rx1", rate="k*A") == {"name": "rx1", "rate": "k*A"}
    assert sbio_tools.modify_reaction("rx1", reversible=True) == {"name": "rx1", "reversible": True}
    assert svc.commands == [
        "set_reaction:rx1:{'rate': 'k*A'}",
        "set_reaction:rx1:{'reversible': True}",
    ]


def test_dose_and_variant_tools_issue_expected_commands(svc: DummyService) -> None:
    assert sbio_tools.create_dose(
        "d1", "drug", dose_type="repeat", amount=100.0, interval=8.0,
        repeat_count=5, amount_units="milligram") == {
        "name": "d1", "target": "drug", "dose_type": "repeat", "amount": 100.0,
        "start_time": None, "interval": 8.0, "repeat_count": 5, "rate": None,
        "amount_units": "milligram", "rate_units": None, "time_units": None,
        "times": None, "amounts": None, "rates": None,
    }
    assert sbio_tools.modify_dose("d1", amount=200.0, target="drug2") == {
        "name": "d1", "target": "drug2", "amount": 200.0,
    }
    assert sbio_tools.list_doses() == ["d1"]
    assert sbio_tools.remove_dose("d1") == {"removed": "d1"}

    assert sbio_tools.create_variant(
        "v1", [{"type": "parameter", "name": "k1", "property": "Value", "value": 0}]) == {
        "name": "v1",
        "content": [{"type": "parameter", "name": "k1", "property": "Value", "value": 0}],
    }
    assert sbio_tools.modify_variant(
        "v1", [{"type": "parameter", "name": "k1", "property": "Value", "value": 0.5}]) == {
        "name": "v1",
        "content": [{"type": "parameter", "name": "k1", "property": "Value", "value": 0.5}],
    }
    assert sbio_tools.list_variants() == ["v1"]
    assert sbio_tools.remove_variant("v1") == {"removed": "v1"}

    assert svc.commands == [
        "add_dose:d1:drug:{'dose_type': 'repeat', 'amount': 100.0, 'start_time': None, "
        "'interval': 8.0, 'repeat_count': 5, 'rate': None, 'amount_units': 'milligram', "
        "'rate_units': None, 'time_units': None, 'times': None, 'amounts': None, 'rates': None}",
        "set_dose:d1:{'target': 'drug2', 'amount': 200.0}",
        "delete_dose:d1",
        "add_variant:v1:[{'type': 'parameter', 'name': 'k1', 'property': 'Value', 'value': 0}]",
        "set_variant:v1:[{'type': 'parameter', 'name': 'k1', 'property': 'Value', 'value': 0.5}]",
        "delete_variant:v1",
    ]


def test_simulation_and_export_tools(svc: DummyService) -> None:
    assert sbio_tools.get_simulation_settings() == {"StopTime": 10.0, "SolverType": "ode15s"}
    assert sbio_tools.configure_simulation(stop_time=5.0, solver_type="ode45") == {
        "StopTime": 10.0,
        "SolverType": "ode15s",
    }
    assert sbio_tools.simulate_model(species=["S2"]) == {
        "time": [0.0, 1.0],
        "names": ["S2"],
        "data": {"S2": [1.0, 0.5]},
    }
    assert sbio_tools.export_graph(path="plot.png", resolution=600) == {
        "path": "plot.png",
        "resolution": 600,
    }
    assert sbio_tools.export_csv() == {
        "csv": "kind,name\r\nspecies,S1\r\nspecies,S2\r\nreaction,R1\r\ncompartment,cell\r\nparameter,k1\r\n",
    }

    assert svc.commands == [
        "set_configset:{'stop_time': 5.0, 'solver_type': 'ode45'}",
        "sim_data = sbiosimulate(m);",
        "axes_handle = sbioplot(sim_data);",
        "fig_handle = get(axes_handle, 'Parent');",
        "exportgraphics(fig_handle, 'plot.png', 'Resolution', 600);",
    ]
