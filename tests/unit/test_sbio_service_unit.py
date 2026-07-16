from __future__ import annotations

from pathlib import Path

import pytest

from simbiology_mcp.core.sbio_service import SbioService
from simbiology_mcp.engine.exceptions import MatlabError, ModelNotFoundError, ProjectNotLoadedError
from simbiology_mcp.engine.matlab_layer import MatlabLayer


@pytest.fixture
def service(monkeypatch: pytest.MonkeyPatch) -> SbioService:
    monkeypatch.setattr(MatlabLayer, "launch", lambda self: None)
    return SbioService()


def test_load_project_populates_models_and_temp_path(service: SbioService, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project = tmp_path / "demo.sbproj"

    def fake_execute(command: str, nargout: int = 0):
        if command == "sbioreset;":
            return None
        if command == f"sbioloadproject('{project}')":
            return None
        if command == "numel(sbioroot().Models)":
            return 2
        if command in {"sbio_model_1 = sbioroot().Models(1);", "sbio_model_2 = sbioroot().Models(2);"}:
            return None
        if command == "sbio_model_1.Name":
            return "one"
        if command == "sbio_model_2.Name":
            return "two"
        raise AssertionError(command)

    monkeypatch.setattr(service, "execute", fake_execute)

    assert service.load_project(str(project)) == ["one", "two"]
    assert service.project_path == str(project)
    assert service.temp_project_path == str(tmp_path / "demo_temp.sbproj")


def test_load_project_maps_matlab_error(service: SbioService, monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_execute(command: str, nargout: int = 0):
        if command == "sbioreset;":
            return None
        raise MatlabError("boom")

    monkeypatch.setattr(service, "execute", fake_execute)

    with pytest.raises(ProjectNotLoadedError, match="Could not load project"):
        service.load_project("missing.sbproj")


def test_create_model_and_get_model_guards(service: SbioService, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(service, "autosave_mutation", lambda: None)
    monkeypatch.setattr(service, "execute", lambda command, nargout=0: None)

    with pytest.raises(ProjectNotLoadedError):
        service.create_model("demo")

    service._models = {"one": "m1", "two": "m2"}

    with pytest.raises(ModelNotFoundError, match="Specify a model name"):
        service.get_model()
    with pytest.raises(ModelNotFoundError, match="No model named 'nope'"):
        service.get_model("nope")

    model = service.rename_model("one", "renamed")
    assert model.name == "renamed"
    assert service.model_names() == ["two", "renamed"]


def test_execute_delegates_to_matlab_layer(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(MatlabLayer, "launch", lambda self: None)
    called: list[tuple[str, int]] = []
    monkeypatch.setattr(MatlabLayer, "execute", lambda self, command, nargout=0: called.append((command, nargout)) or "ok")
    service = SbioService()

    assert service.execute("disp(1)", 1) == "ok"
    assert called == [("disp(1)", 1)]


def test_target_path_and_default_stem_helpers(service: SbioService) -> None:
    with pytest.raises(ProjectNotLoadedError):
        service._target_path(None)

    service.project_path = "demo.sbproj"
    assert service._target_path(None) == "demo.sbproj"
    assert service._default_stem() == "simbiology"
    service._models = {"named": "m"}
    assert service._default_stem() == "named"

