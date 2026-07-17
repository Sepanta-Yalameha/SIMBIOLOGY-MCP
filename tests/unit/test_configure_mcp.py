from __future__ import annotations

import io
import json
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


def test_resolve_client_executable_prefers_pathext_shim(monkeypatch) -> None:
    # Windows ships client CLIs as a .cmd/.bat shim next to an extensionless
    # shell script. Only the shim is spawnable, so the bare match must not win.
    available = {"code": r"C:\VSCode\bin\code", "code.CMD": r"C:\VSCode\bin\code.cmd"}
    monkeypatch.setattr(configure_mcp.os, "name", "nt")
    monkeypatch.setenv("PATHEXT", ".COM;.EXE;.BAT;.CMD")
    monkeypatch.setattr(configure_mcp.shutil, "which", lambda name: available.get(name))

    assert configure_mcp.resolve_client_executable("code") == r"C:\VSCode\bin\code.cmd"


def test_resolve_client_executable_falls_back_to_bare_name(monkeypatch) -> None:
    monkeypatch.setattr(configure_mcp.os, "name", "posix")
    monkeypatch.setattr(configure_mcp.shutil, "which", lambda name: "/usr/bin/code" if name == "code" else None)

    assert configure_mcp.resolve_client_executable("code") == "/usr/bin/code"


def test_resolve_client_executable_missing_returns_none(monkeypatch) -> None:
    monkeypatch.setattr(configure_mcp.os, "name", "nt")
    monkeypatch.setenv("PATHEXT", ".EXE;.CMD")
    monkeypatch.setattr(configure_mcp.shutil, "which", lambda name: None)

    assert configure_mcp.resolve_client_executable("codex") is None


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


def _record_native(monkeypatch) -> list[list[str]]:
    calls: list[list[str]] = []

    def fake_run(command, *, dry_run, check=True):
        calls.append(command)
        return True

    monkeypatch.setattr(configure_mcp, "resolve_server_launch", lambda: ("sim.exe", ["start"]))
    monkeypatch.setattr(configure_mcp, "_run_native", fake_run)
    return calls


def test_native_add_without_force_does_not_remove(monkeypatch) -> None:
    calls = _record_native(monkeypatch)

    configure_mcp.configure_client("claude-code", scope="user", force=False, dry_run=False)

    assert len(calls) == 1
    assert calls[0][:3] == ["claude", "mcp", "add"]


def test_force_removes_existing_entry_before_native_add(monkeypatch) -> None:
    # `claude mcp add` refuses to overwrite, so --force has to remove first.
    calls = _record_native(monkeypatch)

    configure_mcp.configure_client("claude-code", scope="user", force=True, dry_run=False)

    assert [c[:3] for c in calls] == [["claude", "mcp", "remove"], ["claude", "mcp", "add"]]


def test_force_warns_when_client_cannot_remove(monkeypatch, capsys) -> None:
    calls = _record_native(monkeypatch)

    configure_mcp.configure_client("vscode", scope="user", force=True, dry_run=False)

    assert len(calls) == 1
    assert "--force has no effect" in capsys.readouterr().err


class _FakeCompleted:
    returncode = 0
    stdout = "Added stdio MCP server simbiology with command: C:\\repo\\sim.exe start to project config"
    stderr = ""


def test_native_client_chatter_is_not_relayed(monkeypatch, capsys, tmp_path: Path) -> None:
    # `claude mcp add` narrates the run in its own format and echoes the whole
    # server command back. Report the outcome ourselves instead of relaying it,
    # so every client reads the same.
    kwargs_seen: dict[str, object] = {}

    def fake_run(command, **kwargs):
        kwargs_seen.update(kwargs)
        return _FakeCompleted()

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(configure_mcp, "resolve_server_launch", lambda: ("sim.exe", ["start"]))
    monkeypatch.setattr(configure_mcp, "resolve_client_executable", lambda name: rf"C:\bin\{name}.exe")
    monkeypatch.setattr(configure_mcp.subprocess, "run", fake_run)

    configure_mcp.configure_client("claude-code", scope="project", dry_run=False)

    out = capsys.readouterr().out
    assert "Added the simbiology MCP server for Claude Code (project scope)." in out
    assert "File modified:" in out
    assert "with command" not in out
    assert kwargs_seen.get("capture_output") is True


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
    class _Failed:
        returncode = 1
        stdout = ""
        stderr = "MCP server simbiology already exists in .mcp.json"

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(configure_mcp, "resolve_server_launch", lambda: ("sim.exe", ["start"]))
    monkeypatch.setattr(configure_mcp, "resolve_client_executable", lambda name: rf"C:\bin\{name}.exe")
    monkeypatch.setattr(configure_mcp.subprocess, "run", lambda command, **kwargs: _Failed())

    with pytest.raises(SystemExit) as excinfo:
        configure_mcp.configure_client("claude-code", scope="project", dry_run=False)

    # Capturing output must not swallow why the client refused.
    assert "already exists" in str(excinfo.value)
    assert "--force" in str(excinfo.value)


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


def test_interactive_configure_errors_without_a_terminal(monkeypatch) -> None:
    monkeypatch.setattr(configure_mcp, "_is_interactive", lambda: False)

    with pytest.raises(SystemExit) as excinfo:
        configure_mcp.interactive_configure(noninteractive_fallback="error")

    assert "--client" in str(excinfo.value)


def test_interactive_configure_hints_without_a_terminal(monkeypatch, capsys) -> None:
    monkeypatch.setattr(configure_mcp, "_is_interactive", lambda: False)

    configure_mcp.interactive_configure(noninteractive_fallback="hint")

    assert "--client" in capsys.readouterr().err


def _stub_pickers(monkeypatch, *, client: str | None, scope: str | None) -> list[dict]:
    seen: list[dict] = []
    monkeypatch.setattr(configure_mcp, "_is_interactive", lambda: True)
    monkeypatch.setattr(configure_mcp, "_enable_windows_ansi", lambda: None)
    monkeypatch.setattr(configure_mcp, "_select_client", lambda **kwargs: client)
    monkeypatch.setattr(configure_mcp, "_select_scope", lambda **kwargs: scope)
    monkeypatch.setattr(configure_mcp, "configure_client", lambda name, **kwargs: seen.append({"client": name, **kwargs}))
    return seen


def test_interactive_configure_cancelling_the_client_picker_configures_nothing(monkeypatch, capsys) -> None:
    seen = _stub_pickers(monkeypatch, client=None, scope="user")

    configure_mcp.interactive_configure()

    assert seen == []
    assert "cancelled" in capsys.readouterr().out.casefold()


def test_interactive_configure_cancelling_the_scope_picker_configures_nothing(monkeypatch, capsys) -> None:
    seen = _stub_pickers(monkeypatch, client="cursor", scope=None)

    configure_mcp.interactive_configure()

    assert seen == []
    assert "cancelled" in capsys.readouterr().out.casefold()


def test_interactive_configure_passes_choices_and_flags_through(monkeypatch) -> None:
    seen = _stub_pickers(monkeypatch, client="cursor", scope="project")

    configure_mcp.interactive_configure(force=True, dry_run=True)

    assert seen == [{"client": "cursor", "scope": "project", "force": True, "dry_run": True}]


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
