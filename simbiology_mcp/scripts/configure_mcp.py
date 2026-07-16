"""Configure MCP clients for the SimBiology server."""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from tomlkit import document, dumps, parse, table

from . import tui

SERVER_NAME = "simbiology"

_CLIENT_ORDER = ["claude-code", "cursor", "codex", "windsurf", "copilot-cli", "vscode"]
_CLIENT_LABELS = {
    "claude-code": "Claude Code",
    "cursor": "Cursor",
    "codex": "Codex",
    "windsurf": "Windsurf",
    "copilot-cli": "GitHub Copilot CLI",
    "vscode": "Visual Studio Code / GitHub Copilot",
}
_CLIENT_SCOPES = {
    "claude-code": ("user", "project"),
    "cursor": ("user", "project"),
    "codex": ("user", "project"),
    "windsurf": ("user",),
    "copilot-cli": ("user",),
    "vscode": ("user", "project"),
}


def client_names() -> tuple[str, ...]:
    return tuple(_CLIENT_ORDER)


def supported_scopes(client: str) -> tuple[str, ...]:
    try:
        return _CLIENT_SCOPES[client]
    except KeyError as exc:
        known = ", ".join(_CLIENT_ORDER)
        raise SystemExit(f"Unknown client '{client}'. Known clients: {known}.") from exc


def resolve_server_launch() -> tuple[str, list[str]]:
    python = Path(sys.executable).resolve()
    console_scripts = ("simbiology-mcp.exe", "simbiology-mcp") if os.name == "nt" else ("simbiology-mcp", "simbiology-mcp.exe")
    for script_name in console_scripts:
        console_script = python.parent / script_name
        if console_script.is_file():
            return str(console_script), ["start"]
    return str(python), ["-m", "simbiology_mcp", "start"]


def _user_root() -> Path:
    return Path.home()


def _project_root() -> Path:
    return Path.cwd()


def _is_interactive() -> bool:
    return tui.is_interactive()


def _enable_windows_ansi() -> None:
    tui.enable_windows_ansi()


def _path_for_client(client: str, scope: str) -> Path:
    if scope not in supported_scopes(client):
        raise SystemExit(f"{_CLIENT_LABELS[client]} does not support {scope} scope.")
    root = _user_root() if scope == "user" else _project_root()
    if client == "claude-code":
        return root / (".claude.json" if scope == "user" else ".mcp.json")
    if client == "cursor":
        return root / ".cursor" / "mcp.json"
    if client == "codex":
        return root / ".codex" / "config.toml"
    if client == "windsurf":
        return root / ".codeium" / "windsurf" / "mcp_config.json"
    if client == "copilot-cli":
        return Path(os.environ.get("COPILOT_HOME", str(root / ".copilot"))) / "mcp-config.json"
    if client == "vscode":
        return root / ".vscode" / "mcp.json"
    raise SystemExit(f"Unknown client '{client}'.")


def _server_config() -> dict[str, Any]:
    command, args = resolve_server_launch()
    return {"command": command, "args": args}


def _render_native_command(client: str, scope: str) -> list[str]:
    command, args = resolve_server_launch()
    if client == "claude-code":
        return ["claude", "mcp", "add", "--transport", "stdio", "--scope", scope, SERVER_NAME, "--", command, *args]
    if client == "codex":
        return ["codex", "mcp", "add", SERVER_NAME, "--", command, *args]
    if client == "copilot-cli":
        return ["copilot", "mcp", "add", SERVER_NAME, "--", command, *args]
    if client == "vscode" and scope == "user":
        return ["code", "--add-mcp", json.dumps({"name": SERVER_NAME, "type": "stdio", "command": command, "args": args})]
    raise SystemExit(f"{_CLIENT_LABELS[client]} does not support native configuration for {scope} scope.")


def _confirm_replace(path: Path, label: str, scope: str) -> bool:
    prompt = f"Replace the existing {path} configuration for {label} ({scope})? [y/N] "
    answer = input(prompt).strip().casefold()
    return answer in {"y", "yes"}


def _write_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, dir=path.parent, prefix=path.name + ".") as handle:
        handle.write(text)
        temp_path = Path(handle.name)
    if path.exists():
        backup = path.with_suffix(path.suffix + ".bak")
        backup.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    os.replace(temp_path, path)


def merge_json_server(
    path: Path,
    *,
    root_key: str,
    server_name: str,
    server_config: dict[str, Any],
    force: bool,
    dry_run: bool,
) -> None:
    existing_text = path.read_text(encoding="utf-8") if path.exists() else ""
    data: dict[str, Any] = json.loads(existing_text) if existing_text else {}
    if not isinstance(data, dict):
        raise SystemExit(f"{path} must contain a JSON object at the top level.")
    servers = data.get(root_key)
    if servers is None:
        servers = {}
        data[root_key] = servers
    if not isinstance(servers, dict):
        raise SystemExit(f"{path} must contain a JSON object at '{root_key}'.")
    existing = servers.get(server_name)
    if existing == server_config:
        return
    if existing is not None and not force:
        if not _is_interactive():
            raise SystemExit(f"{path} already contains a different {server_name} entry. Re-run with --force.")
        if not _confirm_replace(path, server_name, "project" if path.parent.name == ".vscode" else "user"):
            print("MCP configuration cancelled.")
            return
    servers[server_name] = server_config
    rendered = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    if dry_run:
        print(rendered, end="")
        return
    _write_atomic(path, rendered)


def merge_codex_project_config(
    path: Path,
    *,
    command: str,
    args: list[str],
    force: bool,
    dry_run: bool,
) -> None:
    existing_text = path.read_text(encoding="utf-8") if path.exists() else ""
    doc = parse(existing_text) if existing_text else document()
    servers = doc.get("mcp_servers")
    if servers is None:
        servers = table()
        doc["mcp_servers"] = servers
    elif not hasattr(servers, "get"):
        raise SystemExit(f"{path} must contain a TOML table at 'mcp_servers'.")
    existing = servers.get(SERVER_NAME)
    desired = {"command": command, "args": args}
    if existing is not None and existing == desired:
        return
    if existing is not None and not force:
        if not _is_interactive():
            raise SystemExit(f"{path} already contains a different {SERVER_NAME} entry. Re-run with --force.")
        if not _confirm_replace(path, SERVER_NAME, "project"):
            print("MCP configuration cancelled.")
            return
    server = table()
    server["command"] = command
    server["args"] = args
    servers[SERVER_NAME] = server
    rendered = dumps(doc)
    if not rendered.endswith("\n"):
        rendered += "\n"
    if dry_run:
        print(rendered, end="")
        return
    _write_atomic(path, rendered)


def _configure_json(client: str, scope: str, *, force: bool, dry_run: bool, root_key: str = "mcpServers") -> None:
    path = _path_for_client(client, scope)
    merge_json_server(path, root_key=root_key, server_name=SERVER_NAME, server_config=_server_config(), force=force, dry_run=dry_run)


def _run_native(command: list[str], *, dry_run: bool) -> None:
    if dry_run:
        print(" ".join(shlex.quote(part) for part in command))
        return
    try:
        subprocess.run(command, check=True)
    except FileNotFoundError as exc:
        raise SystemExit(f"Could not run {command[0]}: {exc}") from exc
    except subprocess.CalledProcessError as exc:
        raise SystemExit(f"{command[0]} failed with exit code {exc.returncode}.") from exc
    except OSError as exc:
        raise SystemExit(f"Could not run {command[0]}: {exc}") from exc


def configure_client(
    client: str,
    *,
    scope: str = "user",
    force: bool = False,
    dry_run: bool = False,
) -> None:
    scopes = supported_scopes(client)
    if scope not in scopes:
        raise SystemExit(f"{_CLIENT_LABELS[client]} does not support {scope} scope.")

    if client == "claude-code":
        _run_native(_render_native_command(client, scope), dry_run=dry_run)
        return

    if client == "cursor":
        _configure_json(client, scope, force=force, dry_run=dry_run)
        return

    if client == "codex":
        if scope == "user":
            _run_native(_render_native_command(client, scope), dry_run=dry_run)
            return
        path = _path_for_client(client, scope)
        server = _server_config()
        merge_codex_project_config(path, command=server["command"], args=server["args"], force=force, dry_run=dry_run)
        return

    if client == "windsurf":
        _configure_json(client, scope, force=force, dry_run=dry_run)
        return

    if client == "copilot-cli":
        _run_native(_render_native_command(client, scope), dry_run=dry_run)
        return

    if client == "vscode":
        if scope == "user":
            _run_native(_render_native_command(client, scope), dry_run=dry_run)
            return
        _configure_json(client, scope, force=force, dry_run=dry_run, root_key="servers")
        return

    raise SystemExit(f"Unknown client '{client}'.")


def _select_client(*, read_key=None, stream=None) -> str | None:
    labels = [_CLIENT_LABELS[client] for client in _CLIENT_ORDER] + ["Cancel"]
    title = "Configure the SimBiology MCP Server for which client?  (up/down to move, Enter to select, q to cancel)"
    choice = tui.select(title, labels, read_key=read_key, stream=stream)
    if choice is None or choice == len(labels) - 1:
        return None
    return _CLIENT_ORDER[choice]


def _select_scope(*, client: str, preferred_scope: str | None = None, read_key=None, stream=None) -> str | None:
    scopes = supported_scopes(client)
    if preferred_scope in scopes:
        return preferred_scope
    if len(scopes) == 1:
        return scopes[0]
    labels = ["User", "Project", "Cancel"]
    title = "Configuration scope?"
    choice = tui.select(title, labels, read_key=read_key, stream=stream)
    if choice is None or choice == 2:
        return None
    return "user" if choice == 0 else "project"


def interactive_configure(
    *,
    preferred_scope: str | None = None,
    force: bool = False,
    dry_run: bool = False,
    noninteractive_fallback: str = "error",
) -> None:
    if not _is_interactive():
        if noninteractive_fallback == "hint":
            print(
                "No interactive terminal detected. Re-run with\n"
                "`simbiology-mcp configure --client <client>`.",
                file=sys.stderr,
            )
        elif noninteractive_fallback == "error":
            raise SystemExit(
                "No interactive terminal detected. Re-run with\n`simbiology-mcp configure --client <client>`."
            )
        else:
            print("MCP configuration cancelled.")
        return

    _enable_windows_ansi()
    client = _select_client()
    if client is None:
        print("MCP configuration cancelled.")
        return
    scope = _select_scope(client=client, preferred_scope=preferred_scope)
    if scope is None:
        print("MCP configuration cancelled.")
        return
    configure_client(client, scope=scope, force=force, dry_run=dry_run)


def _list_clients() -> None:
    for client in _CLIENT_ORDER:
        scopes = ", ".join(supported_scopes(client))
        print(f"{_CLIENT_LABELS[client]} ({client}): {scopes}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="simbiology-mcp configure", description="Configure an MCP client for the SimBiology server.")
    parser.add_argument("--client", choices=client_names(), default=None)
    scope = parser.add_mutually_exclusive_group()
    scope.add_argument("--user", action="store_true")
    scope.add_argument("--project", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--list-clients", action="store_true")

    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    if args.list_clients:
        _list_clients()
        return
    if args.client is not None:
        configure_client(args.client, scope="project" if args.project else "user", force=args.force, dry_run=args.dry_run)
        return
    interactive_configure(
        preferred_scope="project" if args.project else None,
        force=args.force,
        dry_run=args.dry_run,
        noninteractive_fallback="error",
    )


if __name__ == "__main__":
    main()
