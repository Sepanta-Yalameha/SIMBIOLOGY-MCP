from __future__ import annotations

import sys
from pathlib import Path

import pytest

import simbiology_mcp.scripts.configure_mcp as configure_mcp
from simbiology_mcp.interfaces import cli
from simbiology_mcp.scripts import get_skill, setup, tui


def test_skill_path_uses_packaged_copy(monkeypatch, tmp_path: Path) -> None:
    packaged = tmp_path / "skills" / "SKILL.md"
    packaged.parent.mkdir(parents=True)
    packaged.write_text("packaged skill", encoding="utf-8")

    monkeypatch.setattr(get_skill, "_packaged_skill_path", lambda: packaged)

    assert get_skill._skill_path() == packaged


def test_write_skill_copies_skill_markdown(monkeypatch, tmp_path: Path) -> None:
    target = tmp_path / "skills" / "SKILL.md"

    source, written = get_skill._write_skill(target)

    assert source == get_skill._skill_path().resolve()
    assert written == target
    assert target.exists()
    assert target.read_text(encoding="utf-8") == get_skill._skill_text()


def test_write_skill_treats_directory_as_install_folder(tmp_path: Path) -> None:
    target_dir = tmp_path / "agent"
    target_dir.mkdir()

    _, written = get_skill._write_skill(target_dir)

    assert written == target_dir / "SKILL.md"
    assert written.read_text(encoding="utf-8") == get_skill._skill_text()


def test_write_skill_treats_extensionless_path_as_install_folder(tmp_path: Path) -> None:
    target_dir = tmp_path / "agent"

    _, written = get_skill._write_skill(target_dir)

    assert written == target_dir / "SKILL.md"
    assert written.read_text(encoding="utf-8") == get_skill._skill_text()


def test_skill_path_falls_back_to_packaged_copy(monkeypatch, tmp_path: Path) -> None:
    packaged = tmp_path / "skills" / "SKILL.md"
    packaged.parent.mkdir(parents=True)
    packaged.write_text("packaged skill", encoding="utf-8")
    monkeypatch.setattr(get_skill, "_packaged_skill_path", lambda: packaged)

    assert get_skill._skill_path() == packaged


def test_get_skill_main_without_args_prints_skill_when_not_a_tty(monkeypatch, capsys) -> None:
    # No flags and no interactive terminal: get-skill prints the skill so the
    # command stays pipeable. A real TTY would instead show the agent picker.
    monkeypatch.setattr(get_skill, "_is_interactive", lambda: False)
    monkeypatch.setattr("sys.argv", ["simbiology-mcp-get-skill"])

    get_skill.main()

    assert capsys.readouterr().out == f"{get_skill._skill_text()}\n"


def test_get_skill_main_prints_skill(monkeypatch, capsys) -> None:
    monkeypatch.setattr("sys.argv", ["simbiology-mcp-get-skill", "--print"])

    get_skill.main()

    assert capsys.readouterr().out == f"{get_skill._skill_text()}\n"


def test_get_skill_main_writes_to_install_path(monkeypatch, capsys, tmp_path: Path) -> None:
    target = tmp_path / "agent" / "SKILL.md"
    monkeypatch.setattr("sys.argv", ["simbiology-mcp-get-skill", "--install-path", str(target)])

    get_skill.main()

    output = capsys.readouterr().out
    assert target.exists()
    assert target.read_text(encoding="utf-8") == get_skill._skill_text()
    assert f"Installed skill to {target.resolve()}" in output


def test_get_skill_main_rejects_print_with_install_path(monkeypatch) -> None:
    monkeypatch.setattr("sys.argv", ["simbiology-mcp-get-skill", "--print", "--install-path", "out"])

    with pytest.raises(SystemExit):
        get_skill.main()


def _fake_keys(sequence: list[str]):
    it = iter(sequence)
    return lambda: next(it)


def test_client_target_resolves_per_client_and_scope(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(get_skill, "_user_root", lambda: tmp_path)
    monkeypatch.setattr(get_skill, "_project_root", lambda: tmp_path)

    cases = {
        ("claude-code", "user"): ".claude/skills",
        ("claude-code", "project"): ".claude/skills",
        ("cursor", "user"): ".cursor/skills",
        ("codex", "user"): ".codex/skills",
        ("codex", "project"): ".agents/skills",
        ("windsurf", "user"): ".codeium/windsurf/skills",
        ("copilot", "user"): ".copilot/skills",
        ("copilot", "project"): ".github/skills",
    }
    for (client, scope), rel in cases.items():
        expected = tmp_path.joinpath(*rel.split("/"), "simbiology-workflow", "SKILL.md")
        assert get_skill._client_target(client, scope) == expected


def test_client_target_rejects_unknown_client() -> None:
    with pytest.raises(SystemExit, match="Unknown client"):
        get_skill._client_target("emacs", "user")


def test_copilot_client_aliases_share_the_copilot_skill_path(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(get_skill, "_project_root", lambda: tmp_path)

    expected = tmp_path / ".github" / "skills" / "simbiology-workflow" / "SKILL.md"
    assert get_skill._client_target("copilot-cli", "project") == expected
    assert get_skill._client_target("vscode", "project") == expected


def test_get_skill_install_user_scope(monkeypatch, capsys, tmp_path: Path) -> None:
    monkeypatch.setattr(get_skill, "_user_root", lambda: tmp_path)
    monkeypatch.setattr("sys.argv", ["simbiology-mcp-get-skill", "--client", "claude-code"])

    get_skill.main()

    target = tmp_path / ".claude" / "skills" / "simbiology-workflow" / "SKILL.md"
    assert target.read_text(encoding="utf-8") == get_skill._skill_text()
    assert f"Installed Claude Code skill to {target.resolve()}" in capsys.readouterr().out


def test_get_skill_install_project_scope(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(get_skill, "_project_root", lambda: tmp_path)
    monkeypatch.setattr("sys.argv", ["simbiology-mcp-get-skill", "--client", "cursor", "--project"])

    get_skill.main()

    assert (tmp_path / ".cursor" / "skills" / "simbiology-workflow" / "SKILL.md").exists()


@pytest.mark.parametrize("scope_flag", ["--project", "--user"])
def test_get_skill_print_rejects_scope_flags(monkeypatch, scope_flag: str) -> None:
    monkeypatch.setattr("sys.argv", ["simbiology-mcp-get-skill", "--print", scope_flag])

    with pytest.raises(SystemExit):
        get_skill.main()


def test_get_skill_install_without_client_prompts_when_interactive(monkeypatch, tmp_path: Path) -> None:
    # A scope flag with no --client should still show the picker.
    monkeypatch.setattr(get_skill, "_is_interactive", lambda: True)
    monkeypatch.setattr(get_skill, "_enable_windows_ansi", lambda: None)
    monkeypatch.setattr(get_skill, "_select_client", lambda **kwargs: "codex")
    monkeypatch.setattr(get_skill, "_project_root", lambda: tmp_path)
    monkeypatch.setattr("sys.argv", ["simbiology-mcp-get-skill", "--project"])

    get_skill.main()

    assert (tmp_path / ".agents" / "skills" / "simbiology-workflow" / "SKILL.md").exists()


def test_get_skill_install_without_client_errors_when_not_interactive(monkeypatch, tmp_path: Path) -> None:
    # Without a terminal to prompt in, a scope flag with no --client errors
    # instead of silently choosing an agent.
    monkeypatch.setattr(get_skill, "_is_interactive", lambda: False)
    monkeypatch.setattr(get_skill, "_user_root", lambda: tmp_path)
    monkeypatch.setattr("sys.argv", ["simbiology-mcp-get-skill", "--project"])

    with pytest.raises(SystemExit):
        get_skill.main()

    assert not (tmp_path / ".claude").exists()


def test_get_skill_install_rejects_unknown_client(monkeypatch) -> None:
    monkeypatch.setattr("sys.argv", ["simbiology-mcp-get-skill", "--client", "emacs"])

    with pytest.raises(SystemExit):
        get_skill.main()


@pytest.mark.parametrize("scope_flag", ["--user", "--project"])
def test_get_skill_install_path_rejects_scope_flags(monkeypatch, scope_flag: str) -> None:
    monkeypatch.setattr("sys.argv", ["simbiology-mcp-get-skill", "--install-path", "out", scope_flag])

    with pytest.raises(SystemExit):
        get_skill.main()


def test_select_client_navigates_and_selects() -> None:
    import io

    chosen = get_skill._select_client(read_key=_fake_keys(["down", "down", "enter"]), stream=io.StringIO())

    assert chosen == get_skill._CLIENT_ORDER[2]


def test_select_client_wraps_up_and_cancels() -> None:
    import io

    up = get_skill._select_client(read_key=_fake_keys(["up", "enter"]), stream=io.StringIO())
    cancelled = get_skill._select_client(read_key=_fake_keys(["cancel"]), stream=io.StringIO())

    assert up == get_skill._CLIENT_ORDER[-1]
    assert cancelled is None


def test_scope_label_shows_install_paths(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(get_skill, "_project_root", lambda: tmp_path / "repo")
    target = tmp_path / "repo" / ".agents" / "skills" / "simbiology-workflow" / "SKILL.md"

    assert get_skill._scope_label("codex", "project") == f"Project - {target}"


def test_select_install_target_uses_selected_scope(monkeypatch, tmp_path: Path) -> None:
    import io

    monkeypatch.setattr(get_skill, "_user_root", lambda: tmp_path / "home")
    monkeypatch.setattr(get_skill, "_project_root", lambda: tmp_path / "repo")

    target = get_skill._select_install_target(client="codex", read_key=_fake_keys(["down", "enter"]), stream=io.StringIO())

    assert target == tmp_path / "repo" / ".agents" / "skills" / "simbiology-workflow" / "SKILL.md"


def test_select_install_target_accepts_custom_path(tmp_path: Path) -> None:
    import io

    target = tmp_path / "custom-skill.md"

    chosen = get_skill._select_install_target(
        client="codex",
        read_key=_fake_keys(["down", "down", "enter"]),
        stream=io.StringIO(),
        input_func=lambda prompt="": str(target),
    )

    assert chosen == target


def test_interactive_install_non_tty_prints_skill(monkeypatch, capsys) -> None:
    monkeypatch.setattr(get_skill, "_is_interactive", lambda: False)

    get_skill.interactive_install(fallback="print")

    assert capsys.readouterr().out == f"{get_skill._skill_text()}\n"


def test_interactive_install_non_tty_hint(monkeypatch, capsys) -> None:
    monkeypatch.setattr(get_skill, "_is_interactive", lambda: False)

    get_skill.interactive_install(fallback="hint")

    assert "no interactive terminal" in capsys.readouterr().err.lower()


def test_interactive_install_writes_selected_client(monkeypatch, capsys, tmp_path: Path) -> None:
    monkeypatch.setattr(get_skill, "_is_interactive", lambda: True)
    monkeypatch.setattr(get_skill, "_enable_windows_ansi", lambda: None)
    monkeypatch.setattr(get_skill, "_select_client", lambda **kwargs: "windsurf")
    monkeypatch.setattr(get_skill, "_user_root", lambda: tmp_path)

    get_skill.interactive_install(scope="user")

    assert (tmp_path / ".codeium" / "windsurf" / "skills" / "simbiology-workflow" / "SKILL.md").exists()
    assert "Installed" in capsys.readouterr().out


def test_interactive_install_prompts_for_missing_scope(monkeypatch, capsys, tmp_path: Path) -> None:
    seen: list[dict] = []

    def fake_select_install_target(**kwargs):
        seen.append(kwargs)
        return tmp_path / "SKILL.md"

    monkeypatch.setattr(get_skill, "_is_interactive", lambda: True)
    monkeypatch.setattr(get_skill, "_enable_windows_ansi", lambda: None)
    monkeypatch.setattr(get_skill, "_select_client", lambda **kwargs: "codex")
    monkeypatch.setattr(get_skill, "_select_install_target", fake_select_install_target)

    get_skill.interactive_install()

    assert seen == [{"client": "codex", "scope": None}]
    assert (tmp_path / "SKILL.md").exists()
    assert str(tmp_path / "SKILL.md") in capsys.readouterr().out


def test_interactive_install_cancelled(monkeypatch, capsys, tmp_path: Path) -> None:
    monkeypatch.setattr(get_skill, "_is_interactive", lambda: True)
    monkeypatch.setattr(get_skill, "_enable_windows_ansi", lambda: None)
    monkeypatch.setattr(get_skill, "_select_client", lambda **kwargs: None)
    monkeypatch.setattr(get_skill, "_user_root", lambda: tmp_path)

    get_skill.interactive_install()

    assert "cancelled" in capsys.readouterr().out.lower()
    assert not (tmp_path / ".claude").exists()


def test_interactive_install_after_configure_installs_for_copilot_alias(monkeypatch) -> None:
    installed: list[tuple[str, str]] = []
    monkeypatch.setattr(tui, "select", lambda *args, **kwargs: 0)
    monkeypatch.setattr(get_skill, "_install_for_client", lambda client, scope: installed.append((client, scope)))

    get_skill.interactive_install_after_configure("vscode", "project")

    assert installed == [("copilot", "project")]


def test_interactive_install_after_configure_opens_full_picker_for_another_location(monkeypatch) -> None:
    calls: list[dict] = []
    monkeypatch.setattr(tui, "select", lambda *args, **kwargs: 2)
    monkeypatch.setattr(get_skill, "interactive_install", lambda **kwargs: calls.append(kwargs))

    get_skill.interactive_install_after_configure("cursor", "user")

    assert calls == [{"fallback": "hint"}]


def test_cli_main_without_args_prints_help(monkeypatch, capsys) -> None:
    monkeypatch.setattr("sys.argv", ["simbiology-mcp"])

    cli.main()

    assert "usage:" in capsys.readouterr().out


def test_cli_start_dispatches_to_server(monkeypatch) -> None:
    called: list[str] = []
    monkeypatch.setattr("sys.argv", ["simbiology-mcp", "start"])
    monkeypatch.setattr(cli, "_run_server", lambda: called.append("start"))

    cli.main()

    assert called == ["start"]


def test_cli_get_skill_dispatches(monkeypatch) -> None:
    called: list[list[str]] = []
    monkeypatch.setattr("sys.argv", ["simbiology-mcp", "get-skill", "--print"])
    monkeypatch.setattr(get_skill, "main", lambda argv=None: called.append(argv or []))

    cli.main()

    assert called == [["--print"]]


def test_cli_get_skill_forwards_project_scope(monkeypatch) -> None:
    captured: list[list[str]] = []
    monkeypatch.setattr("sys.argv", ["simbiology-mcp", "get-skill", "--project"])
    monkeypatch.setattr(get_skill, "main", lambda argv=None: captured.append(argv or []))

    cli.main()

    assert captured == [["--project"]]


def test_cli_get_skill_rejects_client_and_install_path(monkeypatch) -> None:
    captured: list[list[str]] = []
    monkeypatch.setattr("sys.argv", ["simbiology-mcp", "get-skill", "--client", "cursor", "--install-path", "out"])
    monkeypatch.setattr(get_skill, "main", lambda argv=None: captured.append(argv or []))

    with pytest.raises(SystemExit):
        cli.main()


def test_cli_get_skill_bare_forwards_no_flags(monkeypatch) -> None:
    captured: list[list[str]] = []
    monkeypatch.setattr("sys.argv", ["simbiology-mcp", "get-skill"])
    monkeypatch.setattr(get_skill, "main", lambda argv=None: captured.append(argv or []))

    cli.main()

    assert captured == [[]]


def test_cli_get_skill_forwards_user_scope(monkeypatch) -> None:
    captured: list[list[str]] = []
    monkeypatch.setattr("sys.argv", ["simbiology-mcp", "get-skill", "--user"])
    monkeypatch.setattr(get_skill, "main", lambda argv=None: captured.append(argv or []))

    cli.main()

    assert captured == [["--user"]]


def test_cli_setup_dispatches(monkeypatch) -> None:
    called: list[list[str]] = []
    monkeypatch.setattr("sys.argv", ["simbiology-mcp", "setup", "--matlab-index", "1", "--client", "codex", "--project"])
    monkeypatch.setattr(setup, "main", lambda argv=None: called.append(argv or []))

    cli.main()

    assert called == [["--matlab-index", "1", "--client", "codex", "--project"]]


def test_cli_configure_dispatches(monkeypatch) -> None:
    called: list[list[str]] = []
    monkeypatch.setattr("sys.argv", ["simbiology-mcp", "configure", "--client", "codex"])
    monkeypatch.setattr(configure_mcp, "main", lambda argv=None: called.append(argv or []))

    cli.main()

    assert called == [["--client", "codex"]]


def test_tui_select_navigates_and_returns_index() -> None:
    import io

    idx = tui.select("pick", ["a", "b", "c"], read_key=_fake_keys(["down", "down", "enter"]), stream=io.StringIO())

    assert idx == 2


def test_tui_select_cancel_returns_none() -> None:
    import io

    assert tui.select("pick", ["a", "b"], read_key=_fake_keys(["cancel"]), stream=io.StringIO()) is None


def test_tui_select_empty_returns_none() -> None:
    import io

    assert tui.select("nothing", [], stream=io.StringIO()) is None


@pytest.mark.skipif(sys.platform != "win32", reason="Windows key decoding")
def test_read_key_windows_decodes_keys(monkeypatch) -> None:
    import msvcrt

    monkeypatch.setattr(msvcrt, "getwch", _fake_keys(["\xe0", "H"]))
    assert tui.read_key() == "up"
    monkeypatch.setattr(msvcrt, "getwch", _fake_keys(["\xe0", "P"]))
    assert tui.read_key() == "down"
    monkeypatch.setattr(msvcrt, "getwch", _fake_keys(["\r"]))
    assert tui.read_key() == "enter"
    monkeypatch.setattr(msvcrt, "getwch", _fake_keys(["q"]))
    assert tui.read_key() == "cancel"


def test_select_matlab_root_interactive_menu(monkeypatch) -> None:
    installs = [("R2025a", Path("C:/MATLAB/R2025a")), ("R2024b", Path("C:/MATLAB/R2024b"))]
    monkeypatch.setattr(setup, "find_matlab_installs", lambda: installs)
    monkeypatch.setattr(tui, "is_interactive", lambda: True)
    monkeypatch.setattr(tui, "enable_windows_ansi", lambda: None)
    monkeypatch.setattr(tui, "select", lambda *args, **kwargs: 1)

    assert setup.select_matlab_root(None, None) == Path("C:/MATLAB/R2024b")


def test_select_matlab_root_errors_non_interactive_with_multiple(monkeypatch) -> None:
    installs = [("R2025a", Path("C:/MATLAB/R2025a")), ("R2024b", Path("C:/MATLAB/R2024b"))]
    monkeypatch.setattr(setup, "find_matlab_installs", lambda: installs)
    monkeypatch.setattr(tui, "is_interactive", lambda: False)

    with pytest.raises(SystemExit, match="--matlab-index"):
        setup.select_matlab_root(None, None)


def test_select_matlab_root_rejects_out_of_range_index(monkeypatch) -> None:
    monkeypatch.setattr(setup, "find_matlab_installs", lambda: [("R2025a", Path("C:/MATLAB/R2025a")), ("R2024b", Path("C:/MATLAB/R2024b"))])

    with pytest.raises(SystemExit, match="out of range"):
        setup.select_matlab_root(None, 5)


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

    config_calls: list[dict] = []
    monkeypatch.setattr("sys.argv", ["simbiology-mcp-setup", "--matlab-root", str(matlab_root)])
    monkeypatch.setattr(setup.shutil, "which", lambda name: "uv" if name == "uv" else None)
    monkeypatch.setattr(setup.subprocess, "run", fake_run)
    monkeypatch.setattr(setup.tempfile, "gettempdir", lambda: str(tmp_path / "tmp"))
    monkeypatch.setattr(setup, "configure_mcp", configure_mcp)
    monkeypatch.setattr(configure_mcp, "interactive_configure", lambda **kwargs: config_calls.append(kwargs))

    setup.main()

    assert calls[0] == (
        ["uv", "pip", "install", "--python", setup.sys.executable, "setuptools", "wheel"],
        None,
        False,
    )
    assert calls[1][0][0:3] == [setup.sys.executable, "setup.py", "build"]
    assert calls[1][1] == engine_dir
    assert "matlabengine installed successfully." in capsys.readouterr().out
    assert config_calls == [{"preferred_scope": None, "force": False, "dry_run": False, "noninteractive_fallback": "hint"}]


def test_setup_main_installs_matching_skill_for_explicit_client(monkeypatch, tmp_path: Path) -> None:
    matlab_root = tmp_path / "MATLAB" / "R2025a"
    engine_dir = matlab_root / "extern" / "engines" / "python"
    engine_dir.mkdir(parents=True)

    monkeypatch.setattr("sys.argv", ["simbiology-mcp-setup", "--matlab-root", str(matlab_root), "--client", "vscode", "--project"])
    monkeypatch.setattr(setup.shutil, "which", lambda name: "uv")
    monkeypatch.setattr(setup.subprocess, "run", lambda *args, **kwargs: _RunResult(0))
    monkeypatch.setattr(setup.tempfile, "gettempdir", lambda: str(tmp_path / "tmp"))
    configured: list[dict] = []
    installed: list[tuple[str, str]] = []
    monkeypatch.setattr(configure_mcp, "configure_client", lambda client, **kwargs: configured.append({"client": client, **kwargs}))
    monkeypatch.setattr(get_skill, "_install_for_client", lambda client, scope: installed.append((client, scope)))

    setup.main()

    assert configured == [{"client": "vscode", "scope": "project", "force": False, "dry_run": False}]
    assert installed == [("vscode", "project")]


def test_setup_main_offers_skill_install_after_interactive_configuration(monkeypatch, tmp_path: Path) -> None:
    matlab_root = tmp_path / "MATLAB" / "R2025a"
    engine_dir = matlab_root / "extern" / "engines" / "python"
    engine_dir.mkdir(parents=True)

    monkeypatch.setattr("sys.argv", ["simbiology-mcp-setup", "--matlab-root", str(matlab_root)])
    monkeypatch.setattr(setup.shutil, "which", lambda name: "uv")
    monkeypatch.setattr(setup.subprocess, "run", lambda *args, **kwargs: _RunResult(0))
    monkeypatch.setattr(setup.tempfile, "gettempdir", lambda: str(tmp_path / "tmp"))
    monkeypatch.setattr(configure_mcp, "interactive_configure", lambda **kwargs: ("copilot-cli", "project"))
    offered: list[tuple[str, str]] = []
    monkeypatch.setattr(get_skill, "interactive_install_after_configure", lambda client, scope: offered.append((client, scope)))

    setup.main()

    assert offered == [("copilot-cli", "project")]


def test_setup_main_no_skill_skips_matching_skill_for_explicit_client(monkeypatch, tmp_path: Path) -> None:
    matlab_root = tmp_path / "MATLAB" / "R2025a"
    engine_dir = matlab_root / "extern" / "engines" / "python"
    engine_dir.mkdir(parents=True)

    monkeypatch.setattr("sys.argv", ["simbiology-mcp-setup", "--matlab-root", str(matlab_root), "--client", "codex", "--no-skill"])
    monkeypatch.setattr(setup.shutil, "which", lambda name: "uv")
    monkeypatch.setattr(setup.subprocess, "run", lambda *args, **kwargs: _RunResult(0))
    monkeypatch.setattr(setup.tempfile, "gettempdir", lambda: str(tmp_path / "tmp"))
    monkeypatch.setattr(configure_mcp, "configure_client", lambda *args, **kwargs: None)
    monkeypatch.setattr(get_skill, "_install_for_client", lambda *args, **kwargs: pytest.fail("skill should not be installed"))

    setup.main()


def test_setup_main_can_skip_configuration(monkeypatch, tmp_path: Path) -> None:
    matlab_root = tmp_path / "MATLAB" / "R2025a"
    engine_dir = matlab_root / "extern" / "engines" / "python"
    engine_dir.mkdir(parents=True)

    calls: list[tuple[list[str], Path | None, bool | None]] = []

    class Result:
        def __init__(self, returncode: int = 0) -> None:
            self.returncode = returncode

    def fake_run(cmd: list[str], check: bool = False, cwd: Path | None = None):
        calls.append((cmd, cwd, check))
        return Result(0)

    config_calls: list[dict] = []
    monkeypatch.setattr("sys.argv", ["simbiology-mcp-setup", "--matlab-root", str(matlab_root), "--skip-configure"])
    monkeypatch.setattr(setup.shutil, "which", lambda name: "uv" if name == "uv" else None)
    monkeypatch.setattr(setup.subprocess, "run", fake_run)
    monkeypatch.setattr(setup.tempfile, "gettempdir", lambda: str(tmp_path / "tmp"))
    monkeypatch.setattr(setup, "configure_mcp", configure_mcp)
    monkeypatch.setattr(configure_mcp, "interactive_configure", lambda **kwargs: config_calls.append(kwargs))

    setup.main()

    assert calls[1][1] == engine_dir
    assert config_calls == []


def test_setup_main_exits_when_engine_dir_missing(monkeypatch, tmp_path: Path) -> None:
    matlab_root = tmp_path / "MATLAB" / "R2025a"
    monkeypatch.setattr("sys.argv", ["simbiology-mcp-setup", "--matlab-root", str(matlab_root)])

    with pytest.raises(SystemExit, match="MATLAB engine path not found"):
        setup.main()


class _RunResult:
    def __init__(self, returncode: int = 0) -> None:
        self.returncode = returncode


def test_install_build_deps_uses_uv_when_available(monkeypatch) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(setup.shutil, "which", lambda name: r"C:\uv.exe" if name == "uv" else None)
    monkeypatch.setattr(setup.subprocess, "run", lambda cmd, **kw: calls.append(list(cmd)) or _RunResult(0))

    setup._install_build_deps()

    assert calls == [["uv", "pip", "install", "--python", setup.sys.executable, "setuptools", "wheel"]]


def test_install_build_deps_falls_back_to_pip_without_uv(monkeypatch) -> None:
    # The README's plain-pip install path promises `setup` works without uv, so a
    # machine with no uv must bootstrap pip and use it rather than crash on uv.
    calls: list[list[str]] = []
    monkeypatch.setattr(setup.shutil, "which", lambda name: None)
    monkeypatch.setattr(setup.subprocess, "run", lambda cmd, **kw: calls.append(list(cmd)) or _RunResult(0))

    setup._install_build_deps()

    assert calls == [
        [setup.sys.executable, "-m", "ensurepip", "--upgrade"],
        [setup.sys.executable, "-m", "pip", "install", "setuptools", "wheel"],
    ]


def test_install_build_deps_exits_when_install_fails(monkeypatch) -> None:
    def fake_run(cmd: list[str], **kw):
        if "setuptools" in cmd:
            return _RunResult(1)
        return _RunResult(0)

    monkeypatch.setattr(setup.shutil, "which", lambda name: "uv")
    monkeypatch.setattr(setup.subprocess, "run", fake_run)

    with pytest.raises(SystemExit, match="build dependencies"):
        setup._install_build_deps()

