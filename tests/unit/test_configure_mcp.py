from __future__ import annotations

import io
import json
import os
import tomllib
from pathlib import Path

import pytest

import simbiology_mcp.scripts.configure_mcp as configure_mcp


def _fake_keys(sequence: list[str]):
    it = iter(sequence)
    return lambda: next(it)


def test_resolve_server_launch_prefers_console_script(monkeypatch, tmp_path: Path) -> None:
    python = tmp_path / "Scripts" / "python.exe"
    console = tmp_path / "Scripts" / "simbiology-mcp.exe"
    python.parent.mkdir(parents=True)
    python.write_text("", encoding="utf-8")
    console.write_text("", encoding="utf-8")

    monkeypatch.setattr(configure_mcp.sys, "executable", str(python))

    assert configure_mcp.resolve_server_launch() == (str(console.resolve()), ["start"])


def test_resolve_server_launch_falls_back_to_module(monkeypatch, tmp_path: Path) -> None:
    python = tmp_path / "Scripts" / "python.exe"
    python.parent.mkdir(parents=True)
    python.write_text("", encoding="utf-8")

    monkeypatch.setattr(configure_mcp.sys, "executable", str(python))

    assert configure_mcp.resolve_server_launch() == (str(python.resolve()), ["-m", "simbiology_mcp", "start"])


def test_configure_cursor_writes_json(monkeypatch, tmp_path: Path) -> None:
    target = tmp_path / ".cursor" / "mcp.json"
    monkeypatch.setattr(configure_mcp, "_path_for_client", lambda client, scope: target)
    monkeypatch.setattr(configure_mcp, "resolve_server_launch", lambda: (r"C:\repo\.venv\Scripts\simbiology-mcp.exe", ["start"]))
    monkeypatch.setattr(configure_mcp, "_is_interactive", lambda: False)

    configure_mcp.configure_client("cursor", dry_run=False)

    data = json.loads(target.read_text(encoding="utf-8"))
    assert data == {
        "mcpServers": {
            "simbiology": {
                "command": r"C:\repo\.venv\Scripts\simbiology-mcp.exe",
                "args": ["start"],
            }
        }
    }


def test_configure_codex_writes_toml(monkeypatch, tmp_path: Path) -> None:
    target = tmp_path / ".codex" / "config.toml"
    target.parent.mkdir(parents=True)
    target.write_text("# keep\n[mcp_servers.other]\ncommand = \"x\"\n", encoding="utf-8")
    monkeypatch.setattr(configure_mcp, "_path_for_client", lambda client, scope: target)
    monkeypatch.setattr(configure_mcp, "resolve_server_launch", lambda: (r"C:\repo\.venv\Scripts\python.exe", ["-m", "simbiology_mcp", "start"]))
    monkeypatch.setattr(configure_mcp, "_is_interactive", lambda: False)

    configure_mcp.configure_client("codex", scope="project", dry_run=False)

    text = target.read_text(encoding="utf-8")
    assert "# keep" in text
    assert "[mcp_servers.other]" in text
    data = tomllib.loads(text)
    assert data["mcp_servers"]["simbiology"]["command"] == r"C:\repo\.venv\Scripts\python.exe"
    assert data["mcp_servers"]["simbiology"]["args"] == ["-m", "simbiology_mcp", "start"]


windows_only = pytest.mark.skipif(os.name != "nt", reason="PATHEXT resolution is Windows-specific")


def _assert_same_path(actual: str | None, expected: Path) -> None:
    # PATHEXT is conventionally uppercase, so the resolved extension may not match
    # the file's own casing. Windows does not care, and neither should this.
    assert actual is not None
    assert actual.casefold() == str(expected).casefold()


@windows_only
def test_resolve_client_executable_prefers_pathext_shim_over_bare_script(monkeypatch, tmp_path: Path) -> None:
    # Real files, because the bug was in shutil.which's real behaviour: VS Code
    # ships an extensionless shell script beside code.cmd, and which() returns
    # the script, which is unspawnable (WinError 193).
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "code").write_text("#!/bin/sh\n", encoding="utf-8")
    (bin_dir / "code.cmd").write_text("@echo off\n", encoding="utf-8")
    monkeypatch.setenv("PATH", str(bin_dir))
    monkeypatch.setenv("PATHEXT", ".COM;.EXE;.BAT;.CMD")

    _assert_same_path(configure_mcp.resolve_client_executable("code"), bin_dir / "code.cmd")


@windows_only
def test_resolve_client_executable_takes_the_earlier_directory(monkeypatch, tmp_path: Path) -> None:
    # Windows resolves a bare command directory-first: an earlier directory wins
    # whatever its extension. Probing each extension across the whole PATH would
    # let this stray .exe beat the real .cmd, because .EXE precedes .CMD.
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    (first / "code.cmd").write_text("@echo off\n", encoding="utf-8")
    (second / "code.exe").write_bytes(b"MZ")
    monkeypatch.setenv("PATH", os.pathsep.join([str(first), str(second)]))
    monkeypatch.setenv("PATHEXT", ".COM;.EXE;.BAT;.CMD")

    _assert_same_path(configure_mcp.resolve_client_executable("code"), first / "code.cmd")


@windows_only
def test_resolve_client_executable_survives_empty_pathext(monkeypatch, tmp_path: Path) -> None:
    # PATHEXT set-but-empty must still fall back to the defaults, or nothing is
    # ever probed and the unspawnable bare name wins again.
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "code").write_text("#!/bin/sh\n", encoding="utf-8")
    (bin_dir / "code.cmd").write_text("@echo off\n", encoding="utf-8")
    monkeypatch.setenv("PATH", str(bin_dir))
    monkeypatch.setenv("PATHEXT", "")

    _assert_same_path(configure_mcp.resolve_client_executable("code"), bin_dir / "code.cmd")


def test_resolve_client_executable_falls_back_to_bare_name(monkeypatch) -> None:
    monkeypatch.setattr(configure_mcp.os, "name", "posix")
    monkeypatch.setattr(configure_mcp.shutil, "which", lambda name: "/usr/bin/code" if name == "code" else None)

    assert configure_mcp.resolve_client_executable("code") == "/usr/bin/code"


def test_resolve_client_executable_missing_returns_none(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("PATH", str(tmp_path))
    monkeypatch.setattr(configure_mcp.shutil, "which", lambda name: None)

    assert configure_mcp.resolve_client_executable("codex") is None


@windows_only
@pytest.mark.parametrize("metacharacter", ["&", "|", "<", ">", "^"])
def test_batch_launcher_refuses_cmd_metacharacters(tmp_path: Path, metacharacter: str) -> None:
    # cmd.exe would execute these rather than pass them along, so a venv under
    # e.g. C:\R&D must fail loudly rather than be handed to a .cmd launcher.
    launcher = tmp_path / "code.cmd"
    launcher.write_text("@echo off\n", encoding="utf-8")

    with pytest.raises(SystemExit) as excinfo:
        configure_mcp._reject_unsafe_batch_arguments(str(launcher), ["code", "--add-mcp", rf"C:\R{metacharacter}D\sim.exe"])

    assert "cmd.exe" in str(excinfo.value)


@windows_only
def test_batch_launcher_allows_ordinary_payloads(tmp_path: Path) -> None:
    # The --add-mcp payload always contains quotes and backslashes; only cmd
    # metacharacters are a problem, so this must not become a false refusal.
    launcher = tmp_path / "code.cmd"
    launcher.write_text("@echo off\n", encoding="utf-8")
    payload = json.dumps({"name": "simbiology", "command": r"C:\Program Files (x86)\py\sim.exe", "args": ["start"]})

    configure_mcp._reject_unsafe_batch_arguments(str(launcher), ["code", "--add-mcp", payload])


def test_exe_launcher_is_not_subject_to_cmd_rules(tmp_path: Path) -> None:
    # An .exe is spawned directly, so cmd.exe never sees the arguments.
    launcher = tmp_path / "claude.exe"
    launcher.write_bytes(b"MZ")

    configure_mcp._reject_unsafe_batch_arguments(str(launcher), ["claude", "mcp", "add", r"C:\R&D\sim.exe"])


def test_merge_json_server_reads_config_with_bom(tmp_path: Path) -> None:
    # Editors and shells on Windows routinely save JSON with a BOM.
    target = tmp_path / "mcp.json"
    target.write_text('{"mcpServers": {"other": {"command": "x"}}}', encoding="utf-8-sig")

    configure_mcp.merge_json_server(
        target,
        root_key="mcpServers",
        server_name="simbiology",
        server_config={"command": "c", "args": ["start"]},
        force=False,
        dry_run=False,
    )

    data = json.loads(target.read_text(encoding="utf-8"))
    assert data["mcpServers"]["other"] == {"command": "x"}
    assert data["mcpServers"]["simbiology"] == {"command": "c", "args": ["start"]}


def test_merge_json_server_rejects_malformed_json(tmp_path: Path) -> None:
    target = tmp_path / "mcp.json"
    target.write_text("{ this is not json", encoding="utf-8")

    with pytest.raises(SystemExit) as excinfo:
        configure_mcp.merge_json_server(
            target,
            root_key="mcpServers",
            server_name="simbiology",
            server_config={"command": "c", "args": ["start"]},
            force=False,
            dry_run=False,
        )

    assert "not valid JSON" in str(excinfo.value)


def test_merge_codex_config_rejects_malformed_toml(tmp_path: Path) -> None:
    target = tmp_path / "config.toml"
    target.write_text("[[[not toml", encoding="utf-8")

    with pytest.raises(SystemExit) as excinfo:
        configure_mcp.merge_codex_project_config(target, command="c", args=["start"], force=False, dry_run=False)

    assert "not valid TOML" in str(excinfo.value)


def test_configure_vscode_project_declares_stdio_type(monkeypatch, tmp_path: Path) -> None:
    target = tmp_path / ".vscode" / "mcp.json"
    monkeypatch.setattr(configure_mcp, "_path_for_client", lambda client, scope: target)
    monkeypatch.setattr(configure_mcp, "resolve_server_launch", lambda: (r"C:\repo\.venv\Scripts\simbiology-mcp.exe", ["start"]))
    monkeypatch.setattr(configure_mcp, "_is_interactive", lambda: False)

    configure_mcp.configure_client("vscode", scope="project", dry_run=False)

    data = json.loads(target.read_text(encoding="utf-8"))
    assert data["servers"]["simbiology"] == {
        "type": "stdio",
        "command": r"C:\repo\.venv\Scripts\simbiology-mcp.exe",
        "args": ["start"],
    }


def test_copilot_cli_config_path_is_under_copilot_home(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(configure_mcp, "_user_root", lambda: tmp_path)

    assert configure_mcp._path_for_client("copilot-cli", "user") == tmp_path / ".copilot" / "mcp-config.json"


def test_configure_copilot_cli_writes_local_server(monkeypatch, capsys, tmp_path: Path) -> None:
    # Copilot CLI stores MCP servers in ~/.copilot/mcp-config.json under an
    # `mcpServers` root, with `type: "local"`. Writing that file directly works
    # whether or not the standalone @github/copilot CLI is installed, unlike
    # shelling out to `copilot mcp add`, which cannot be trusted on a machine
    # that only has the VS Code bootstrapper shim.
    target = tmp_path / ".copilot" / "mcp-config.json"
    monkeypatch.setattr(configure_mcp, "_path_for_client", lambda client, scope: target)
    monkeypatch.setattr(configure_mcp, "resolve_server_launch", lambda: (r"C:\repo\.venv\Scripts\simbiology-mcp.exe", ["start"]))
    monkeypatch.setattr(configure_mcp, "_is_interactive", lambda: False)

    configure_mcp.configure_client("copilot-cli", scope="user", dry_run=False)

    out = capsys.readouterr().out
    assert "Added the simbiology MCP server for GitHub Copilot CLI (user scope)." in out
    assert f"File modified: {target}" in out
    assert json.loads(target.read_text(encoding="utf-8")) == {
        "mcpServers": {
            "simbiology": {
                "type": "local",
                "command": r"C:\repo\.venv\Scripts\simbiology-mcp.exe",
                "args": ["start"],
            }
        }
    }

    # A re-run finds the identical entry and is a no-op success, not an error.
    configure_mcp.configure_client("copilot-cli", scope="user", dry_run=False)
    assert "already configured for GitHub Copilot CLI (user scope)." in capsys.readouterr().out


def _record_native(monkeypatch, *, fail_add_with: str | None = None) -> list[list[str]]:
    """Record every native command, optionally making the first `add` refuse."""

    calls: list[list[str]] = []

    def fake_run(command, *, dry_run, check=True):
        calls.append(command)
        is_add = "add" in command or "--add-mcp" in command
        if is_add and fail_add_with and not any("add" in c or "--add-mcp" in c for c in calls[:-1]):
            raise SystemExit(fail_add_with)
        return True

    monkeypatch.setattr(configure_mcp, "resolve_server_launch", lambda: ("sim.exe", ["start"]))
    monkeypatch.setattr(configure_mcp, "_run_native", fake_run)
    return calls


def test_native_add_on_a_fresh_machine_never_removes(monkeypatch) -> None:
    # Nothing is configured yet, so a remove would be pointless and its failure
    # would be the only thing standing between the user and a working install.
    calls = _record_native(monkeypatch)

    configure_mcp.configure_client("claude-code", scope="user", force=True, dry_run=False)

    assert [c[:3] for c in calls] == [["claude", "mcp", "add"]]


def test_force_removes_only_after_the_add_is_refused(monkeypatch) -> None:
    calls = _record_native(monkeypatch, fail_add_with="MCP server simbiology already exists")

    configure_mcp.configure_client("claude-code", scope="user", force=True, dry_run=False)

    # Add first: a remove that ran before a doomed add would leave nothing behind.
    assert [c[:3] for c in calls] == [
        ["claude", "mcp", "add"],
        ["claude", "mcp", "remove"],
        ["claude", "mcp", "add"],
    ]


def test_native_rerun_without_force_reports_already_configured(monkeypatch, capsys) -> None:
    # A benign re-run that finds our entry already present must be a no-op success,
    # not an error -- otherwise `simbiology-mcp setup` fails at its last step every
    # time it is run twice. Only the add runs, and it reports like a file-writing
    # client reports an unchanged config.
    calls = _record_native(monkeypatch, fail_add_with="MCP server simbiology already exists")

    configure_mcp.configure_client("claude-code", scope="user", force=False, dry_run=False)

    assert [c[:3] for c in calls] == [["claude", "mcp", "add"]]
    assert "already configured for Claude Code (user scope)." in capsys.readouterr().out


def test_native_rerun_detects_alternate_already_configured_wording(monkeypatch, capsys) -> None:
    # Idempotency must not hinge on one CLI's exact phrasing: each client words a
    # duplicate differently, so a family of markers is recognised.
    calls = _record_native(monkeypatch, fail_add_with="server 'simbiology' is already configured")

    configure_mcp.configure_client("codex", scope="user", force=False, dry_run=False)

    assert [c[:3] for c in calls] == [["codex", "mcp", "add"]]
    assert "already configured for Codex (user scope)." in capsys.readouterr().out


def test_force_reports_when_client_cannot_remove(monkeypatch, capsys) -> None:
    calls = _record_native(monkeypatch, fail_add_with="server already exists")

    with pytest.raises(SystemExit) as excinfo:
        configure_mcp.configure_client("vscode", scope="user", force=True, dry_run=False)

    assert len(calls) == 1
    assert "no command to remove" in str(excinfo.value)
    # Nothing was written, so nothing may be claimed.
    assert "File modified" not in capsys.readouterr().out


def test_native_clients_are_not_given_a_guessed_path(monkeypatch, capsys) -> None:
    # These clients pick their own file and honour relocations we do not track,
    # so naming one would sometimes be a lie.
    _record_native(monkeypatch)

    configure_mcp.configure_client("claude-code", scope="user", force=False, dry_run=False)

    out = capsys.readouterr().out
    assert "Added the simbiology MCP server for Claude Code (user scope)." in out
    assert "File modified" not in out


_CLAUDE_CHATTER = "Added stdio MCP server simbiology with command: C:\\repo\\sim.exe start to project config"


class _FakeCompleted:
    returncode = 0
    stdout = _CLAUDE_CHATTER
    stderr = ""


def test_native_client_chatter_is_not_relayed(monkeypatch, capsys, tmp_path: Path) -> None:
    # `claude mcp add` narrates the run in its own format and echoes the whole
    # server command back. Report the outcome ourselves instead of relaying it,
    # so every client reads the same.
    def fake_run(command, **kwargs):
        # Stand in for a child that inherited the terminal: if the output is not
        # captured, its chatter lands on our stdout for real.
        if not kwargs.get("capture_output"):
            print(_CLAUDE_CHATTER)
        return _FakeCompleted()

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(configure_mcp, "resolve_server_launch", lambda: ("sim.exe", ["start"]))
    monkeypatch.setattr(configure_mcp, "resolve_client_executable", lambda name: rf"C:\bin\{name}.exe")
    monkeypatch.setattr(configure_mcp.subprocess, "run", fake_run)

    configure_mcp.configure_client("claude-code", scope="project", dry_run=False)

    out = capsys.readouterr().out
    assert "Added the simbiology MCP server for Claude Code (project scope)." in out
    assert "with command" not in out


def test_native_client_errors_are_stripped_of_colour(monkeypatch, tmp_path: Path) -> None:
    # Clients colour their output even when piped, so the escapes would reach a
    # plain console as literal junk.
    class _Failed:
        returncode = 1
        stdout = ""
        stderr = "\x1b[31mnot logged in; run `claude login`\x1b[39m"

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(configure_mcp, "resolve_server_launch", lambda: ("sim.exe", ["start"]))
    monkeypatch.setattr(configure_mcp, "resolve_client_executable", lambda name: rf"C:\bin\{name}.exe")
    monkeypatch.setattr(configure_mcp.subprocess, "run", lambda command, **kwargs: _Failed())

    with pytest.raises(SystemExit) as excinfo:
        configure_mcp.configure_client("claude-code", scope="project", force=False, dry_run=False)

    assert "\x1b[" not in str(excinfo.value)
    assert "not logged in" in str(excinfo.value)


def test_file_writing_client_reports_the_same_way(monkeypatch, capsys, tmp_path: Path) -> None:
    target = tmp_path / ".cursor" / "mcp.json"
    monkeypatch.setattr(configure_mcp, "_path_for_client", lambda client, scope: target)
    monkeypatch.setattr(configure_mcp, "resolve_server_launch", lambda: ("sim.exe", ["start"]))
    monkeypatch.setattr(configure_mcp, "_is_interactive", lambda: False)

    configure_mcp.configure_client("cursor", scope="user", dry_run=False)
    first = capsys.readouterr().out
    assert "Added the simbiology MCP server for Cursor (user scope)." in first
    assert f"File modified: {target}" in first

    configure_mcp.configure_client("cursor", scope="user", dry_run=False)
    assert "already configured for Cursor (user scope)." in capsys.readouterr().out


def test_native_failure_surfaces_client_error(monkeypatch, tmp_path: Path) -> None:
    # A genuine failure (not a pre-existing entry) must still surface: capturing
    # the CLI's output so every client reports uniformly must not swallow the
    # real reason the client refused.
    class _Failed:
        returncode = 1
        stdout = ""
        stderr = "failed to write config: permission denied"

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(configure_mcp, "resolve_server_launch", lambda: ("sim.exe", ["start"]))
    monkeypatch.setattr(configure_mcp, "resolve_client_executable", lambda name: rf"C:\bin\{name}.exe")
    monkeypatch.setattr(configure_mcp.subprocess, "run", lambda command, **kwargs: _Failed())

    with pytest.raises(SystemExit) as excinfo:
        configure_mcp.configure_client("claude-code", scope="project", dry_run=False)

    assert "permission denied" in str(excinfo.value)


def test_select_client_navigates_and_selects() -> None:
    chosen = configure_mcp._select_client(read_key=_fake_keys(["down", "down", "enter"]), stream=io.StringIO())

    assert chosen == configure_mcp._CLIENT_ORDER[2]


def test_select_client_cancel_row_and_quit_both_return_none() -> None:
    # "Cancel" is the last row, so one press of up from the top lands on it.
    on_cancel_row = configure_mcp._select_client(read_key=_fake_keys(["up", "enter"]), stream=io.StringIO())
    quit_key = configure_mcp._select_client(read_key=_fake_keys(["cancel"]), stream=io.StringIO())

    assert on_cancel_row is None
    assert quit_key is None


def test_select_scope_skips_prompt_for_single_scope_client() -> None:
    # Windsurf only supports user scope, so there is nothing to ask.
    assert configure_mcp._select_scope(client="windsurf") == "user"


def test_select_scope_honours_preferred_scope() -> None:
    assert configure_mcp._select_scope(client="cursor", preferred_scope="project") == "project"


@pytest.mark.parametrize(
    ("keys", "expected"),
    [
        (["enter"], "user"),
        (["down", "enter"], "project"),
        (["down", "down", "enter"], None),
    ],
)
def test_select_scope_menu(keys: list[str], expected: str | None) -> None:
    assert configure_mcp._select_scope(client="cursor", read_key=_fake_keys(keys), stream=io.StringIO()) == expected


def test_scope_label_shows_known_config_paths(monkeypatch, tmp_path: Path) -> None:
    target = tmp_path / "mcp.json"
    monkeypatch.setattr(configure_mcp, "_path_for_client", lambda client, scope: target)

    assert configure_mcp._scope_label("cursor", "user") == f"User - {target}"


@pytest.mark.parametrize(
    ("keys", "expected"),
    [
        (["enter"], False),
        (["down", "enter"], True),
        (["down", "down", "enter"], None),
    ],
)
def test_select_dry_run_menu(keys: list[str], expected: bool | None) -> None:
    assert configure_mcp._select_dry_run(read_key=_fake_keys(keys), stream=io.StringIO()) is expected


def test_interactive_configure_errors_without_a_terminal(monkeypatch) -> None:
    monkeypatch.setattr(configure_mcp, "_is_interactive", lambda: False)

    with pytest.raises(SystemExit) as excinfo:
        configure_mcp.interactive_configure(noninteractive_fallback="error")

    assert "--client" in str(excinfo.value)


def test_interactive_configure_hints_without_a_terminal(monkeypatch, capsys) -> None:
    monkeypatch.setattr(configure_mcp, "_is_interactive", lambda: False)

    configure_mcp.interactive_configure(noninteractive_fallback="hint")

    assert "--client" in capsys.readouterr().err


def _stub_pickers(monkeypatch, *, client: str | None, scope: str | None) -> tuple[list[dict], list[dict]]:
    """Stub both pickers. Returns (configure_client calls, _select_scope kwargs)."""

    seen: list[dict] = []
    scope_kwargs: list[dict] = []

    def fake_select_scope(**kwargs):
        scope_kwargs.append(kwargs)
        return scope

    monkeypatch.setattr(configure_mcp, "_is_interactive", lambda: True)
    monkeypatch.setattr(configure_mcp, "_enable_windows_ansi", lambda: None)
    monkeypatch.setattr(configure_mcp, "_select_client", lambda **kwargs: client)
    monkeypatch.setattr(configure_mcp, "_select_scope", fake_select_scope)
    monkeypatch.setattr(configure_mcp, "configure_client", lambda name, **kwargs: seen.append({"client": name, **kwargs}))
    return seen, scope_kwargs


def test_interactive_configure_cancelling_the_client_picker_configures_nothing(monkeypatch, capsys) -> None:
    seen, _ = _stub_pickers(monkeypatch, client=None, scope="user")

    configure_mcp.interactive_configure()

    assert seen == []
    assert "cancelled" in capsys.readouterr().out.casefold()


def test_interactive_configure_cancelling_the_scope_picker_configures_nothing(monkeypatch, capsys) -> None:
    seen, _ = _stub_pickers(monkeypatch, client="cursor", scope=None)

    configure_mcp.interactive_configure()

    assert seen == []
    assert "cancelled" in capsys.readouterr().out.casefold()


def test_interactive_configure_passes_choices_and_flags_through(monkeypatch) -> None:
    seen, _ = _stub_pickers(monkeypatch, client="cursor", scope="project")

    configure_mcp.interactive_configure(force=True, dry_run=True)

    assert seen == [{"client": "cursor", "scope": "project", "force": True, "dry_run": True}]


def test_interactive_configure_can_prompt_for_dry_run(monkeypatch) -> None:
    seen, _ = _stub_pickers(monkeypatch, client="cursor", scope="project")
    monkeypatch.setattr(configure_mcp, "_select_dry_run", lambda **kwargs: True)

    configure_mcp.interactive_configure(dry_run=None)

    assert seen == [{"client": "cursor", "scope": "project", "force": False, "dry_run": True}]


def test_interactive_configure_forwards_preferred_scope_to_the_picker(monkeypatch) -> None:
    # `configure --project` reaches the scope picker only through this argument;
    # dropping it would silently ignore the flag.
    _, scope_kwargs = _stub_pickers(monkeypatch, client="cursor", scope="project")

    configure_mcp.interactive_configure(preferred_scope="project")

    assert scope_kwargs == [{"client": "cursor", "preferred_scope": "project"}]


def test_replace_prompt_declined_leaves_config_untouched(monkeypatch, tmp_path: Path) -> None:
    target = tmp_path / "mcp.json"
    target.write_text('{"mcpServers": {"simbiology": {"command": "OLD", "args": []}}}', encoding="utf-8")
    monkeypatch.setattr(configure_mcp, "_is_interactive", lambda: True)
    monkeypatch.setattr("builtins.input", lambda prompt="": "n")

    status = configure_mcp.merge_json_server(
        target,
        root_key="mcpServers",
        server_name="simbiology",
        server_config={"command": "NEW", "args": ["start"]},
        force=False,
        dry_run=False,
    )

    assert status == configure_mcp.CANCELLED
    assert "OLD" in target.read_text(encoding="utf-8")


def test_replace_prompt_accepted_writes_config(monkeypatch, tmp_path: Path) -> None:
    target = tmp_path / "mcp.json"
    target.write_text('{"mcpServers": {"simbiology": {"command": "OLD", "args": []}}}', encoding="utf-8")
    monkeypatch.setattr(configure_mcp, "_is_interactive", lambda: True)
    monkeypatch.setattr("builtins.input", lambda prompt="": "y")

    status = configure_mcp.merge_json_server(
        target,
        root_key="mcpServers",
        server_name="simbiology",
        server_config={"command": "NEW", "args": ["start"]},
        force=False,
        dry_run=False,
    )

    assert status == configure_mcp.WRITTEN
    assert "NEW" in target.read_text(encoding="utf-8")
