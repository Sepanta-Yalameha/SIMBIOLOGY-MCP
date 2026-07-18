"""Configure MCP clients for the SimBiology server."""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from tomlkit import document, dumps, parse, table
from tomlkit.exceptions import ParseError

from . import tui

SERVER_NAME = "simbiology"

# Outcome of configuring one client. The writers report which of these happened
# and `configure_client` does the talking, so every client reports identically.
WRITTEN = "written"
UNCHANGED = "unchanged"
CANCELLED = "cancelled"
DRY_RUN = "dry-run"

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


_DEFAULT_PATHEXT = ".COM;.EXE;.BAT;.CMD"

# Client CLIs colour their output even when it is piped, so relayed errors would
# otherwise arrive as escape sequences on a plain console.
_ANSI_PATTERN = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


def _strip_ansi(text: str) -> str:
    return _ANSI_PATTERN.sub("", text)


def resolve_client_executable(name: str) -> str | None:
    """Resolve a client CLI name to a path `subprocess` can actually spawn.

    Client CLIs ship as script shims on Windows rather than real executables
    (`code.cmd`, `copilot.bat`), and CreateProcess only ever appends `.exe`, so a
    bare name fails with WinError 2. A plain `shutil.which(name)` is not enough
    either: it matches an extensionless shell script sitting beside the shim,
    which then fails with WinError 193.

    Walk directories first and extensions second, which is the order Windows
    itself resolves a bare command in: an earlier directory always wins, whatever
    its extension. Probing every directory per extension instead would let a
    stray `code.exe` late on PATH beat the real `code.cmd` early on it.
    """
    if os.name != "nt":
        return shutil.which(name)

    # `or` rather than a get() default: PATHEXT set-but-empty must fall back too,
    # otherwise no extension is ever tried and we are back to WinError 193.
    extensions = [ext.strip() for ext in (os.environ.get("PATHEXT") or _DEFAULT_PATHEXT).split(os.pathsep) if ext.strip()]
    for directory in (os.environ.get("PATH") or "").split(os.pathsep):
        if not directory:
            continue
        for extension in extensions:
            candidate = Path(directory) / (name + extension)
            if candidate.is_file():
                return str(candidate)
    # Nothing spawnable on PATH. Return None so the caller reports a clean
    # "not on PATH" message; falling back to shutil.which here would hand back
    # the extensionless script this resolver exists to reject (WinError 193).
    return None


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
        return root / ".copilot" / "mcp-config.json"
    if client == "vscode":
        return root / ".vscode" / "mcp.json"
    raise SystemExit(f"Unknown client '{client}'.")


def _server_config(*, server_type: str | None = None) -> dict[str, Any]:
    command, args = resolve_server_launch()
    config: dict[str, Any] = {}
    if server_type is not None:
        config["type"] = server_type
    config["command"] = command
    config["args"] = args
    return config


def _render_native_command(client: str, scope: str) -> list[str]:
    command, args = resolve_server_launch()
    if client == "claude-code":
        return ["claude", "mcp", "add", "--transport", "stdio", "--scope", scope, SERVER_NAME, "--", command, *args]
    if client == "codex":
        return ["codex", "mcp", "add", SERVER_NAME, "--", command, *args]
    if client == "vscode" and scope == "user":
        return ["code", "--add-mcp", json.dumps({"name": SERVER_NAME, "type": "stdio", "command": command, "args": args})]
    raise SystemExit(f"{_CLIENT_LABELS[client]} does not support native configuration for {scope} scope.")


def _render_native_remove_command(client: str, scope: str) -> list[str] | None:
    """Command that drops an existing entry, for clients whose CLI can remove one.

    `claude mcp add` and `codex mcp add` both refuse to overwrite an existing
    server, so --force has to remove the old entry first. Clients missing from
    this table have no documented remove verb, so --force cannot be honoured.
    """
    if client == "claude-code":
        return ["claude", "mcp", "remove", "--scope", scope, SERVER_NAME]
    if client == "codex":
        return ["codex", "mcp", "remove", SERVER_NAME]
    return None


# Each client CLI words a pre-existing entry differently, so match the family
# rather than one literal: without this, a benign re-run against a CLI that does
# not happen to say "already exists" crashes instead of being a no-op.
_ALREADY_CONFIGURED_MARKERS = ("already exists", "already configured", "already registered")


def _is_already_configured(message: str) -> bool:
    lowered = message.casefold()
    return any(marker in lowered for marker in _ALREADY_CONFIGURED_MARKERS)


def _run_native_configure(client: str, scope: str, *, force: bool, dry_run: bool) -> str:
    """Register with a client through its own CLI.

    Adds first and only removes if the add is refused, so a failed --force can
    never leave the user with no entry at all: unlike the files written here,
    a client's own config gets no .bak to fall back on. It also keeps the
    pointless remove off machines that have nothing configured yet.
    """
    add = _render_native_command(client, scope)
    try:
        _run_native(add, dry_run=dry_run)
        return DRY_RUN if dry_run else WRITTEN
    except SystemExit as exc:
        message = str(exc)
        if not _is_already_configured(message):
            raise
        if not force:
            # A re-run that finds our entry already present is a no-op success,
            # the same outcome a file-writing client reports as UNCHANGED. We
            # cannot read a native client's own file to confirm it is byte
            # identical, but a same-named entry is almost certainly the one we
            # added before, and --force still forces a clean replace.
            return UNCHANGED
        remove = _render_native_remove_command(client, scope)
        if remove is None:
            raise SystemExit(f"{message}\n--force cannot replace it: {_CLIENT_LABELS[client]} has no command to remove an entry. Edit its configuration by hand.") from exc

    _run_native(remove, dry_run=dry_run)
    _run_native(add, dry_run=dry_run)
    return WRITTEN


def _confirm_replace(path: Path, label: str) -> bool:
    prompt = f"Replace the existing {label} entry in {path}? [y/N] "
    answer = input(prompt).strip().casefold()
    return answer in {"y", "yes"}


def _read_existing(path: Path) -> str:
    """Read a config we are about to merge into.

    Decoded as utf-8-sig because editors and shells on Windows routinely save
    JSON with a BOM, which utf-8 keeps as a leading \\ufeff and every parser then
    rejects. utf-8-sig strips a BOM when present and is a no-op when absent.
    """
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8-sig")


def _write_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, dir=path.parent, prefix=path.name + ".") as handle:
        handle.write(text)
        temp_path = Path(handle.name)
    if path.exists():
        backup = path.with_suffix(path.suffix + ".bak")
        # Copied as bytes so the backup is byte-identical to whatever was there.
        backup.write_bytes(path.read_bytes())
    os.replace(temp_path, path)


def merge_json_server(
    path: Path,
    *,
    root_key: str,
    server_name: str,
    server_config: dict[str, Any],
    force: bool,
    dry_run: bool,
) -> str:
    existing_text = _read_existing(path)
    try:
        data: dict[str, Any] = json.loads(existing_text) if existing_text.strip() else {}
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{path} is not valid JSON ({exc}). Fix or remove the file, then re-run.") from exc
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
        return UNCHANGED
    if existing is not None and not force:
        if not _is_interactive():
            raise SystemExit(f"{path} already contains a different {server_name} entry. Re-run with --force.")
        if not _confirm_replace(path, server_name):
            return CANCELLED
    servers[server_name] = server_config
    rendered = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    if dry_run:
        print(rendered, end="")
        return DRY_RUN
    _write_atomic(path, rendered)
    return WRITTEN


def merge_codex_project_config(
    path: Path,
    *,
    command: str,
    args: list[str],
    force: bool,
    dry_run: bool,
) -> str:
    existing_text = _read_existing(path)
    try:
        doc = parse(existing_text) if existing_text.strip() else document()
    except ParseError as exc:
        raise SystemExit(f"{path} is not valid TOML ({exc}). Fix or remove the file, then re-run.") from exc
    servers = doc.get("mcp_servers")
    if servers is None:
        servers = table()
        doc["mcp_servers"] = servers
    elif not hasattr(servers, "get"):
        raise SystemExit(f"{path} must contain a TOML table at 'mcp_servers'.")
    existing = servers.get(SERVER_NAME)
    desired = {"command": command, "args": args}
    if existing is not None and existing == desired:
        return UNCHANGED
    if existing is not None and not force:
        if not _is_interactive():
            raise SystemExit(f"{path} already contains a different {SERVER_NAME} entry. Re-run with --force.")
        if not _confirm_replace(path, SERVER_NAME):
            return CANCELLED
    server = table()
    server["command"] = command
    server["args"] = args
    servers[SERVER_NAME] = server
    rendered = dumps(doc)
    if not rendered.endswith("\n"):
        rendered += "\n"
    if dry_run:
        print(rendered, end="")
        return DRY_RUN
    _write_atomic(path, rendered)
    return WRITTEN


def _configure_json(client: str, scope: str, *, force: bool, dry_run: bool, root_key: str = "mcpServers", server_type: str | None = None) -> str:
    path = _path_for_client(client, scope)
    return merge_json_server(path, root_key=root_key, server_name=SERVER_NAME, server_config=_server_config(server_type=server_type), force=force, dry_run=dry_run)


_BATCH_SUFFIXES = (".bat", ".cmd")

# Live syntax to cmd.exe. `"` is deliberately absent: it is what desyncs the
# quoting rather than what exploits it, and every --add-mcp payload contains it.
_CMD_METACHARACTERS = "&|<>^"

# Client CLIs may block on a prompt we would never see, so cap the wait.
_NATIVE_TIMEOUT_SECONDS = 120


def _reject_unsafe_batch_arguments(executable: str, command: list[str]) -> None:
    """Refuse to hand cmd.exe metacharacters it would execute.

    A .bat/.cmd launcher is run by cmd.exe, so its command line is parsed twice:
    by cmd.exe, then by the program using MSVCRT rules. subprocess quotes for the
    second parse only, escaping `"` as `\\"`, which cmd.exe does not honour. Quote
    state desyncs and any metacharacter left in the line becomes live syntax
    (CVE-2024-3566, "BatBadBut") -- a path like C:\\R&D\\.venv would both break the
    call and be executable. Quoting correctly around a double parse is famously
    unreliable, so refuse instead of risking it.
    """
    if os.name != "nt" or not executable.casefold().endswith(_BATCH_SUFFIXES):
        return
    for argument in command[1:]:
        found = [character for character in _CMD_METACHARACTERS if character in argument]
        if found:
            raise SystemExit(
                f"Cannot configure {Path(executable).name} safely: an argument contains {' '.join(found)}, "
                f"which cmd.exe would execute rather than pass along.\nConfigure this client by hand instead."
            )


def _run_native(command: list[str], *, dry_run: bool, check: bool = True) -> bool:
    """Run a client's own CLI. Returns True when the command succeeded.

    Output is captured rather than inherited so that every client reports the
    same way here: each CLI otherwise announces the run in its own format, and
    `claude mcp add` in particular echoes the whole server command back. On
    failure the captured text is surfaced so the real error is not swallowed.
    """
    if dry_run:
        print(subprocess.list2cmdline(command) if os.name == "nt" else " ".join(shlex.quote(part) for part in command))
        return True
    executable = resolve_client_executable(command[0])
    if executable is None:
        raise SystemExit(f"Could not find '{command[0]}' on PATH. Install it, or configure this client by hand.")
    _reject_unsafe_batch_arguments(executable, command)
    try:
        # stdin is closed rather than inherited: with output captured, a CLI that
        # prompted would block on input while its question sat unread in a pipe.
        result = subprocess.run([executable, *command[1:]], capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=_NATIVE_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired as exc:
        raise SystemExit(f"{command[0]} did not finish within {_NATIVE_TIMEOUT_SECONDS}s. Configure this client by hand.") from exc
    except OSError as exc:
        raise SystemExit(f"Could not run {command[0]}: {exc}") from exc
    if result.returncode == 0:
        return True
    if not check:
        return False
    detail = _strip_ansi((result.stderr or result.stdout or "").strip())
    failure = f"{command[0]} failed with exit code {result.returncode}."
    raise SystemExit(f"{failure}\n{detail}" if detail else failure)


def _writes_own_file(client: str, scope: str) -> bool:
    """Whether we edit this client's config ourselves rather than call its CLI."""

    if client in {"cursor", "windsurf", "copilot-cli"}:
        return True
    return client in {"codex", "vscode"} and scope == "project"


def _display_path(client: str, scope: str) -> Path | None:
    """Config file to name in the result, when we can name it honestly.

    Only claimed for configs written here. The clients configured through their
    own CLI choose where to write, and honour relocations we do not track
    (CLAUDE_CONFIG_DIR, CODEX_HOME), so naming a path for them would be a guess
    that is sometimes simply wrong.
    """
    if not _writes_own_file(client, scope):
        return None
    return _path_for_client(client, scope)


def _announce(client: str, scope: str, status: str) -> None:
    label = _CLIENT_LABELS[client]
    if status == CANCELLED:
        print("MCP configuration cancelled.")
        return
    if status == UNCHANGED:
        print(f"{SERVER_NAME} is already configured for {label} ({scope} scope).")
        return
    if status == WRITTEN:
        print(f"Added the {SERVER_NAME} MCP server for {label} ({scope} scope).")
        path = _display_path(client, scope)
        if path is not None:
            print(f"File modified: {path}")
        return
    raise AssertionError(f"unhandled configuration status {status!r}")


def _apply_client_config(client: str, scope: str, *, force: bool, dry_run: bool) -> str:
    if client == "claude-code":
        return _run_native_configure(client, scope, force=force, dry_run=dry_run)

    if client == "cursor":
        return _configure_json(client, scope, force=force, dry_run=dry_run)

    if client == "codex":
        if scope == "user":
            return _run_native_configure(client, scope, force=force, dry_run=dry_run)
        server = _server_config()
        return merge_codex_project_config(_path_for_client(client, scope), command=server["command"], args=server["args"], force=force, dry_run=dry_run)

    if client == "windsurf":
        return _configure_json(client, scope, force=force, dry_run=dry_run)

    if client == "copilot-cli":
        # Copilot CLI reads ~/.copilot/mcp-config.json (root `mcpServers`, local
        # servers typed "local"), so write it directly. Shelling out to
        # `copilot mcp add` would depend on the standalone CLI being installed and,
        # against the VS Code bootstrapper shim, can exit 0 without configuring.
        return _configure_json(client, scope, force=force, dry_run=dry_run, root_key="mcpServers", server_type="local")

    if client == "vscode":
        if scope == "user":
            return _run_native_configure(client, scope, force=force, dry_run=dry_run)
        # VS Code infers stdio from `command`, but state it so the file matches
        # the documented schema and the user-scope entry `code --add-mcp` writes.
        return _configure_json(client, scope, force=force, dry_run=dry_run, root_key="servers", server_type="stdio")

    raise SystemExit(f"Unknown client '{client}'.")


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

    status = _apply_client_config(client, scope, force=force, dry_run=dry_run)
    # A dry run has already printed the config or command it would have used.
    if status != DRY_RUN:
        _announce(client, scope, status)


def _select_client(*, read_key=None, stream=None) -> str | None:
    labels = [f"{_CLIENT_LABELS[client]} [{', '.join(supported_scopes(client))}]" for client in _CLIENT_ORDER] + ["Cancel"]
    title = "Configure the SimBiology MCP Server for which client?  (up/down to move, Enter to select, q to cancel)"
    choice = tui.select(title, labels, read_key=read_key, stream=stream)
    if choice is None or choice == len(labels) - 1:
        return None
    return _CLIENT_ORDER[choice]


def _scope_label(client: str, scope: str) -> str:
    path = _display_path(client, scope)
    if path is not None:
        return f"{scope.title()} - {path}"
    return f"{scope.title()} - via {_CLIENT_LABELS[client]} CLI"


def _select_dry_run(*, read_key=None, stream=None) -> bool | None:
    labels = ["Write configuration", "Dry run only", "Cancel"]
    title = "Configure now or preview the changes first?"
    choice = tui.select(title, labels, read_key=read_key, stream=stream)
    if choice is None or choice == 2:
        return None
    return choice == 1


def _select_scope(*, client: str, preferred_scope: str | None = None, read_key=None, stream=None) -> str | None:
    scopes = supported_scopes(client)
    if preferred_scope in scopes:
        return preferred_scope
    if len(scopes) == 1:
        return scopes[0]
    labels = [_scope_label(client, "user"), _scope_label(client, "project"), "Cancel"]
    title = "Configuration scope?"
    choice = tui.select(title, labels, read_key=read_key, stream=stream)
    if choice is None or choice == 2:
        return None
    return "user" if choice == 0 else "project"


def interactive_configure(
    *,
    preferred_scope: str | None = None,
    force: bool = False,
    dry_run: bool | None = False,
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
    if dry_run is None:
        dry_run = _select_dry_run()
        if dry_run is None:
            print("MCP configuration cancelled.")
            return
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
        print(f"{client}: [{scopes}]")


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
        if not args.project and not args.user and _is_interactive():
            _enable_windows_ansi()
            dry_run = args.dry_run
            if not dry_run:
                selected_dry_run = _select_dry_run()
                if selected_dry_run is None:
                    print("MCP configuration cancelled.")
                    return
                dry_run = selected_dry_run
            scope = _select_scope(client=args.client)
            if scope is None:
                print("MCP configuration cancelled.")
                return
            configure_client(args.client, scope=scope, force=args.force, dry_run=dry_run)
            return
        configure_client(args.client, scope="project" if args.project else "user", force=args.force, dry_run=args.dry_run)
        return
    interactive_configure(
        preferred_scope="project" if args.project else None,
        force=args.force,
        dry_run=True if args.dry_run else None,
        noninteractive_fallback="error",
    )


if __name__ == "__main__":
    main()
