from __future__ import annotations

import json
import tomllib
from pathlib import Path

import pytest

import simbiology_mcp.configure_mcp as configure_mcp


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


def test_resolve_server_launch_uses_unix_console_script(monkeypatch, tmp_path: Path) -> None:
    python = tmp_path / "bin" / "python"
    console = tmp_path / "bin" / "simbiology-mcp"
    python.parent.mkdir(parents=True)
    python.write_text("", encoding="utf-8")
    console.write_text("", encoding="utf-8")

    monkeypatch.setattr(configure_mcp.sys, "executable", str(python))
    monkeypatch.setattr(configure_mcp.os, "name", "posix")

    assert configure_mcp.resolve_server_launch() == (str(console.resolve()), ["start"])


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


def test_interactive_configure_uses_client_picker(monkeypatch) -> None:
    called: list[tuple[str, dict[str, object]]] = []
    monkeypatch.setattr(configure_mcp, "_is_interactive", lambda: True)
    monkeypatch.setattr(configure_mcp, "_select_client", lambda **kwargs: "codex")
    monkeypatch.setattr(configure_mcp, "_select_scope", lambda **kwargs: "user")
    monkeypatch.setattr(configure_mcp, "configure_client", lambda client, **kwargs: called.append((client, kwargs)))

    configure_mcp.interactive_configure()

    assert called == [("codex", {"scope": "user", "force": False, "dry_run": False})]
