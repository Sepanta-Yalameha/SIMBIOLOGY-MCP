from __future__ import annotations

from pathlib import Path

import pytest

from scripts import get_skill, setup


def test_skill_path_prefers_repo_root() -> None:
    assert get_skill._skill_path() == get_skill._repo_skill_path()


def test_write_skill_copies_skill_markdown(tmp_path: Path) -> None:
    target = tmp_path / "skills" / "SKILL.md"

    source, written = get_skill._write_skill(target)

    assert source == get_skill._skill_path().resolve()
    assert written == target
    assert target.exists()
    assert target.read_text(encoding="utf-8").startswith("---\nname: using-simbiology-mcp")


def test_skill_path_falls_back_to_packaged_copy(monkeypatch, tmp_path: Path) -> None:
    packaged = tmp_path / "skills" / "simbiology_workflow" / "SKILL.md"
    packaged.parent.mkdir(parents=True)
    packaged.write_text("packaged skill", encoding="utf-8")
    missing_repo = tmp_path / "missing" / "SKILL.md"

    monkeypatch.setattr(get_skill, "_repo_skill_path", lambda: missing_repo)
    monkeypatch.setattr(get_skill, "_packaged_skill_path", lambda: packaged)

    assert get_skill._skill_path() == packaged


def test_get_skill_main_without_args_prints_help(monkeypatch, capsys) -> None:
    monkeypatch.setattr("sys.argv", ["simbiology-mcp-get-skill"])

    get_skill.main()

    assert "usage:" in capsys.readouterr().out


def test_get_skill_main_prints_skill(monkeypatch, capsys) -> None:
    monkeypatch.setattr("sys.argv", ["simbiology-mcp-get-skill", "--print"])

    get_skill.main()

    assert "using-simbiology-mcp" in capsys.readouterr().out


def test_get_skill_main_writes_to_install_path(monkeypatch, capsys, tmp_path: Path) -> None:
    target = tmp_path / "agent" / "SKILL.md"
    monkeypatch.setattr("sys.argv", ["simbiology-mcp-get-skill", "--install-path", str(target)])

    get_skill.main()

    output = capsys.readouterr().out
    assert target.exists()
    assert str(get_skill._skill_path().resolve()) in output
    assert str(target.resolve()) in output


def test_get_skill_main_prints_then_writes(monkeypatch, capsys, tmp_path: Path) -> None:
    target = tmp_path / "agent" / "SKILL.md"
    monkeypatch.setattr("sys.argv", ["simbiology-mcp-get-skill", "--print", "--install-path", str(target)])

    get_skill.main()

    output = capsys.readouterr().out
    assert "using-simbiology-mcp" in output
    assert f"Copied skill from {get_skill._skill_path().resolve()} to {target.resolve()}" in output


def test_select_matlab_root_prefers_explicit_root() -> None:
    root = setup.select_matlab_root("C:/MATLAB/R2025a", None)

    assert root == Path("C:/MATLAB/R2025a")


def test_select_matlab_root_picks_only_install(monkeypatch) -> None:
    monkeypatch.setattr(setup, "find_matlab_installs", lambda: [("R2025a", Path("C:/MATLAB/R2025a"))])

    root = setup.select_matlab_root(None, None)

    assert root == Path("C:/MATLAB/R2025a")


def test_select_matlab_root_uses_index(monkeypatch) -> None:
    installs = [
        ("R2025a", Path("C:/MATLAB/R2025a")),
        ("R2024b", Path("C:/MATLAB/R2024b")),
    ]
    monkeypatch.setattr(setup, "find_matlab_installs", lambda: installs)

    root = setup.select_matlab_root(None, 1)

    assert root == Path("C:/MATLAB/R2024b")


def test_select_matlab_root_exits_when_no_install_found(monkeypatch) -> None:
    monkeypatch.setattr(setup, "find_matlab_installs", lambda: [])

    with pytest.raises(SystemExit, match="No MATLAB installation found"):
        setup.select_matlab_root(None, None)


def test_setup_main_runs_uv_and_engine_install(monkeypatch, tmp_path: Path, capsys) -> None:
    matlab_root = tmp_path / "MATLAB" / "R2025a"
    engine_dir = matlab_root / "extern" / "engines" / "python"
    engine_dir.mkdir(parents=True)

    calls: list[tuple[list[str], Path | None, bool | None]] = []

    class Result:
        def __init__(self, returncode: int = 0) -> None:
            self.returncode = returncode

    def fake_run(cmd: list[str], check: bool = False, cwd: Path | None = None):
        calls.append((cmd, cwd, check))
        if check:
            return Result(0)
        return Result(0)

    monkeypatch.setattr("sys.argv", ["simbiology-mcp-setup", "--matlab-root", str(matlab_root)])
    monkeypatch.setattr(setup.subprocess, "run", fake_run)
    monkeypatch.setattr(setup.tempfile, "gettempdir", lambda: str(tmp_path / "tmp"))

    setup.main()

    assert calls[0] == (
        ["uv", "pip", "install", "--python", setup.sys.executable, "setuptools", "wheel"],
        None,
        True,
    )
    assert calls[1][0][0:3] == [setup.sys.executable, "setup.py", "build"]
    assert calls[1][1] == engine_dir
    assert "matlabengine installed successfully." in capsys.readouterr().out


def test_setup_main_exits_when_engine_dir_missing(monkeypatch, tmp_path: Path) -> None:
    matlab_root = tmp_path / "MATLAB" / "R2025a"
    monkeypatch.setattr("sys.argv", ["simbiology-mcp-setup", "--matlab-root", str(matlab_root)])

    with pytest.raises(SystemExit, match="MATLAB engine path not found"):
        setup.main()
