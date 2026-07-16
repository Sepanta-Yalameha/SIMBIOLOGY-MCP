"""Print or install the packaged SimBiology skill markdown.

With no flags this launches an interactive picker (arrow keys) to choose the
agent to install the skill for. Flags (`--client`, `--project`, `--user`,
`--install-path`, `--print`) drive the same behaviour non-interactively.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import tui

# Directory name the skill is installed under. Matches the `name` in SKILL.md's
# frontmatter so the folder and the agent's skill invocation stay consistent.
SKILL_DIR_NAME = "simbiology-workflow"

# Where each client auto-discovers skills, per scope. The user-scope path is
# resolved against the home directory and the project-scope path against the
# current working directory. Paths verified against each client's docs (Jul 2026);
# Codex reads `~/.codex/skills` at user scope and `.agents/skills` in a repo.
_CLIENT_SKILL_DIRS: dict[str, dict[str, Path]] = {
    "claude-code": {"user": Path(".claude") / "skills", "project": Path(".claude") / "skills"},
    "cursor": {"user": Path(".cursor") / "skills", "project": Path(".cursor") / "skills"},
    "codex": {"user": Path(".codex") / "skills", "project": Path(".agents") / "skills"},
    "windsurf": {"user": Path(".codeium") / "windsurf" / "skills", "project": Path(".windsurf") / "skills"},
    "copilot": {"user": Path(".copilot") / "skills", "project": Path(".github") / "skills"},
}

# Menu order and human-readable labels for the interactive picker.
_CLIENT_ORDER = ["claude-code", "cursor", "codex", "windsurf", "copilot"]
_CLIENT_LABELS = {
    "claude-code": "Claude Code",
    "cursor": "Cursor",
    "codex": "Codex",
    "windsurf": "Windsurf",
    "copilot": "GitHub Copilot",
}


def _packaged_skill_path() -> Path:
    return Path(__file__).resolve().parents[1] / "skills" / "SKILL.md"


def _skill_path() -> Path:
    return _packaged_skill_path()


def _skill_text() -> str:
    return _skill_path().read_text(encoding="utf-8")


def _user_root() -> Path:
    return Path.home()


def _project_root() -> Path:
    return Path.cwd()


def _client_target(client: str, scope: str) -> Path:
    """Resolve the SKILL.md destination for a known client and scope."""

    try:
        base_rel = _CLIENT_SKILL_DIRS[client][scope]
    except KeyError:
        known = ", ".join(sorted(_CLIENT_SKILL_DIRS))
        raise SystemExit(f"Unknown client '{client}'. Known clients: {known}.")
    root = _user_root() if scope == "user" else _project_root()
    return root / base_rel / SKILL_DIR_NAME / "SKILL.md"


def _install_target(path: Path) -> Path:
    expanded = path.expanduser()
    # An existing directory, or a non-existent path with no file extension, is
    # treated as a folder to drop SKILL.md into. An existing file (even without
    # an extension) or a path with a suffix is used as the literal target.
    if expanded.is_dir() or (expanded.suffix == "" and not expanded.exists()):
        expanded = expanded / "SKILL.md"
    return expanded.resolve()


def _write_skill(path: Path) -> tuple[Path, Path]:
    source = _skill_path().resolve()
    target = _install_target(path)
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(_skill_text(), encoding="utf-8")
    except OSError as exc:
        raise SystemExit(f"Could not write skill to {target}: {exc}") from exc
    return source, target


def _is_interactive() -> bool:
    return tui.is_interactive()


def _enable_windows_ansi() -> None:
    tui.enable_windows_ansi()


def _select_client(*, read_key=None, stream=None) -> str | None:
    """Show the arrow-key agent menu; return the chosen client key or None."""

    labels = [_CLIENT_LABELS[k] for k in _CLIENT_ORDER]
    title = "Install the SimBiology skill for which agent?  (up/down to move, Enter to select, q to cancel)"
    choice = tui.select(title, labels, read_key=read_key, stream=stream)
    return None if choice is None else _CLIENT_ORDER[choice]


def _install_for_client(client: str, scope: str) -> None:
    _, target = _write_skill(_client_target(client, scope))
    print(f"Installed {_CLIENT_LABELS[client]} skill to {target}")


def interactive_install(*, scope: str = "user", fallback: str = "print") -> None:
    """Pick a client with the arrow-key menu and install the skill at `scope`.

    With no interactive terminal, `fallback` decides what happens: `"print"`
    prints SKILL.md (so `get-skill` stays pipeable), `"hint"` prints a short note
    on how to install non-interactively, and `"error"` exits asking for --client
    (used when install was requested but no agent could be chosen).
    """

    if not _is_interactive():
        if fallback == "hint":
            print(
                "Skill not installed: no interactive terminal detected. Install it with "
                "`simbiology-mcp get-skill --client <claude-code|cursor|codex|windsurf|copilot>`.",
                file=sys.stderr,
            )
        elif fallback == "error":
            raise SystemExit("No interactive terminal to choose an agent. Re-run with --client <claude-code|cursor|codex|windsurf|copilot>.")
        else:
            print(_skill_text())
        return

    _enable_windows_ansi()
    client = _select_client()
    if client is None:
        print("Skill installation cancelled.")
        return
    _install_for_client(client, scope)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="simbiology-mcp get-skill",
        description="Install or print the packaged SimBiology workflow skill (SKILL.md). With no flags, pick an agent interactively.",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--print", action="store_true", dest="print_skill", help="Print SKILL.md to stdout.")
    mode.add_argument("--client", choices=sorted(_CLIENT_SKILL_DIRS), default=None, help="Install directly for a client. Combine with --user or --project to choose scope.")
    mode.add_argument("--install-path", help="Install directly to an explicit path.")
    scope = parser.add_mutually_exclusive_group()
    scope.add_argument("--user", action="store_true", help="Install into the user-level skills directory (default).")
    scope.add_argument("--project", action="store_true", help="Install into the current project's skills directory.")

    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    scope_name = "project" if args.project else "user"

    if args.print_skill:
        if args.project or args.user:
            parser.error("--user and --project cannot be used with --print")
        print(_skill_text())
        return

    if args.install_path is not None:
        if args.project or args.user:
            parser.error("--user and --project cannot be used with --install-path")
        _, target = _write_skill(Path(args.install_path))
        print(f"Installed skill to {target}")
        return

    if args.client is not None:
        _install_for_client(args.client, scope_name)
        return

    if args.project or args.user:
        # An explicit scope means the user asked for installation, so fail fast
        # instead of silently printing when we cannot open the picker.
        interactive_install(scope=scope_name, fallback="error")
        return

    interactive_install(scope="user", fallback="print")

if __name__ == "__main__":
    main()
