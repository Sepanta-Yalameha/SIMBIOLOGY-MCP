"""Print or install the packaged SimBiology skill markdown.

With no flags this launches an interactive picker (arrow keys) to choose the
agent to install the skill for. Flags (`--install`, `--client`, `--project`,
`--install-path`, `--print`) drive the same behaviour non-interactively, and a
non-interactive terminal falls back to printing SKILL.md so the output stays
pipeable.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Directory name the skill is installed under. Matches the `name` in SKILL.md's
# frontmatter so the folder and the agent's skill invocation stay consistent.
SKILL_DIR_NAME = "simbiology-workflow"

# Where each client auto-discovers skills, per scope. The user-scope path is
# resolved against the home directory and the project-scope path against the
# current working directory. Paths verified against each client's official docs
# (Jul 2026). Codex uses the current-official `~/.agents/skills` (its legacy
# `~/.codex/skills` still works but is deprecated).
_CLIENT_SKILL_DIRS: dict[str, dict[str, Path]] = {
    "claude-code": {"user": Path(".claude") / "skills", "project": Path(".claude") / "skills"},
    "cursor": {"user": Path(".cursor") / "skills", "project": Path(".cursor") / "skills"},
    "codex": {"user": Path(".agents") / "skills", "project": Path(".agents") / "skills"},
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
    try:
        return sys.stdin.isatty() and sys.stdout.isatty()
    except (AttributeError, ValueError):
        return False


def _enable_windows_ansi() -> None:
    """Best-effort enable of ANSI escape handling on Windows consoles."""

    if sys.platform != "win32":
        return
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        # STD_OUTPUT_HANDLE = -11; mode 7 enables virtual-terminal processing.
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    except Exception:
        pass


def _read_key() -> str:
    """Read one keypress and normalize it to up/down/enter/cancel/'' (other)."""

    if sys.platform == "win32":
        import msvcrt

        ch = msvcrt.getwch()
        if ch in ("\x00", "\xe0"):
            return {"H": "up", "P": "down"}.get(msvcrt.getwch(), "")
        if ch in ("\r", "\n"):
            return "enter"
        if ch in ("\x1b", "q", "Q", "\x03"):
            return "cancel"
        return ""

    import select
    import termios
    import tty

    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        ch = sys.stdin.read(1)
        if ch == "\x1b":
            # Peek for an arrow escape sequence without blocking on a bare Esc.
            if select.select([sys.stdin], [], [], 0.01)[0]:
                if sys.stdin.read(1) == "[" and select.select([sys.stdin], [], [], 0.01)[0]:
                    return {"A": "up", "B": "down"}.get(sys.stdin.read(1), "")
            return "cancel"
        if ch in ("\r", "\n"):
            return "enter"
        if ch in ("q", "Q", "\x03"):
            return "cancel"
        return ""
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def _render_menu(title: str, labels: list[str], index: int, stream) -> None:
    lines = [title]
    for i, label in enumerate(labels):
        pointer = ">" if i == index else " "
        lines.append(f" {pointer} {label}")
    stream.write("\n".join(lines) + "\n")
    stream.flush()


def _select_client(*, read_key=_read_key, stream=None) -> str | None:
    """Show an arrow-key menu of clients; return the chosen key or None."""

    stream = stream or sys.stdout
    labels = [_CLIENT_LABELS[k] for k in _CLIENT_ORDER]
    title = "Install the SimBiology skill for which agent?  (up/down to move, Enter to select, q to cancel)"
    index = 0
    _render_menu(title, labels, index, stream)
    height = len(labels) + 1
    while True:
        key = read_key()
        if key == "up":
            index = (index - 1) % len(_CLIENT_ORDER)
        elif key == "down":
            index = (index + 1) % len(_CLIENT_ORDER)
        elif key == "enter":
            return _CLIENT_ORDER[index]
        elif key == "cancel":
            return None
        else:
            continue
        stream.write(f"\x1b[{height}A")  # move cursor back up to redraw in place
        _render_menu(title, labels, index, stream)


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
                "Skill not installed: no interactive terminal detected. Install it with " "`simbiology-mcp get-skill --install --client <claude-code|cursor|codex|windsurf|copilot>`.",
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
    parser.add_argument("--print", action="store_true", dest="print_skill", help="Print SKILL.md to stdout.")
    parser.add_argument("--install", action="store_true", help="Install SKILL.md into the target client's skills directory (no prompt).")
    parser.add_argument("--client", choices=sorted(_CLIENT_SKILL_DIRS), default=None, help="Client to install for. Omit with --install to choose from the interactive menu.")
    scope = parser.add_mutually_exclusive_group()
    scope.add_argument("--user", action="store_true", help="Install into the user-level skills directory (default).")
    scope.add_argument("--project", action="store_true", help="Install into the current project's skills directory.")
    parser.add_argument("--install-path", help="Install to an explicit path instead of a client skills directory.")

    args = parser.parse_args(sys.argv[1:] if argv is None else argv)

    if args.print_skill:
        print(_skill_text())

    if args.install_path is not None:
        _, target = _write_skill(Path(args.install_path))
        print(f"Installed skill to {target}")
    elif args.install:
        scope_name = "project" if args.project else "user"
        if args.client is not None:
            _install_for_client(args.client, scope_name)
        else:
            # No agent named: choose from the menu, keeping the chosen scope.
            # With no interactive terminal there is nothing to prompt, so error.
            interactive_install(scope=scope_name, fallback="error")
    elif not args.print_skill:
        interactive_install(scope="user", fallback="print")


if __name__ == "__main__":
    main()
