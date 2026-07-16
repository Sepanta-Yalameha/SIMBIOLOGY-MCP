from __future__ import annotations

from pathlib import Path

import pytest

from simbiology_mcp.core.sbio_service import SbioService
from simbiology_mcp.core.sbio_model import to_matlab_string
from simbiology_mcp.engine.exceptions import AutosaveError
from simbiology_mcp.engine.matlab_layer import MatlabLayer


@pytest.fixture
def service(monkeypatch: pytest.MonkeyPatch) -> SbioService:
    monkeypatch.setattr(MatlabLayer, "launch", lambda self: None)
    return SbioService()


def test_create_project_with_path_writes_actual_and_temp_projects(service: SbioService, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    commands: list[str] = []
    monkeypatch.setattr(service, "execute", lambda command, nargout=0: commands.append(command))

    target = tmp_path / "model.sbproj"
    assert service.create_project("demo", str(target)) == ["demo"]

    assert service.project_path == str(target)
    assert service.temp_project_path == str(tmp_path / "model_temp.sbproj")
    assert commands == [
        "sbioreset;",
        "m = sbiomodel('demo');",
        f"sbiosaveproject({to_matlab_string(str(target))},'m')",
        f"sbiosaveproject({to_matlab_string(str(tmp_path / 'model_temp.sbproj'))},'m')",
    ]


def test_make_temp_project_path_adds_counter_when_needed(service: SbioService, tmp_path: Path) -> None:
    service.project_path = str(tmp_path / "model.sbproj")
    service._models = {"demo": "m"}
    (tmp_path / "model_temp.sbproj").write_text("occupied")

    assert service._make_temp_project_path() == str(tmp_path / "model_temp2.sbproj")


def test_autosave_mutation_wraps_write_errors(service: SbioService, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    service.project_path = str(tmp_path / "model.sbproj")
    service._models = {"demo": "m"}
    monkeypatch.setattr(service, "_write_project", lambda target: (_ for _ in ()).throw(OSError("blocked")))

    with pytest.raises(AutosaveError, match="autosave to recovery project"):
        service.autosave_mutation()

    assert service.temp_project_path == str(tmp_path / "model_temp.sbproj")


def test_save_project_clears_temp_path_even_if_delete_fails(service: SbioService, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    commands: list[str] = []
    monkeypatch.setattr(service, "execute", lambda command, nargout=0: commands.append(command))

    target = tmp_path / "model.sbproj"
    temp_target = tmp_path / "model_temp.sbproj"
    service.project_path = str(target)
    service.temp_project_path = str(temp_target)
    service._models = {"demo": "m"}

    def bad_unlink(self: Path, missing_ok: bool = False) -> None:
        raise OSError("still open")

    monkeypatch.setattr(Path, "unlink", bad_unlink)

    final_target = tmp_path / "final.sbproj"
    service.save_project(str(final_target))

    assert service.project_path == str(final_target)
    assert service.temp_project_path is None
    assert commands == [
        f"sbiosaveproject({to_matlab_string(str(final_target))},'m')",
    ]

