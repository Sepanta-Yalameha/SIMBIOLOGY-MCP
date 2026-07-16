"""Minimal arrow-key selection menu shared by the CLI subcommands.

`select()` renders an in-place list and returns the chosen index (or None if the
user cancels). Key reading is isolated in `read_key()` so callers/tests can inject
their own key source.
"""

from __future__ import annotations

import sys


def is_interactive() -> bool:
    try:
        return sys.stdin.isatty() and sys.stdout.isatty()
    except (AttributeError, ValueError):
        return False


def enable_windows_ansi() -> None:
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


def read_key() -> str:
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


def _render(title: str, options: list[str], index: int, stream) -> None:
    lines = [title]
    for i, option in enumerate(options):
        pointer = ">" if i == index else " "
        lines.append(f" {pointer} {option}")
    stream.write("\n".join(lines) + "\n")
    stream.flush()


def select(title: str, options: list[str], *, read_key=read_key, stream=None) -> int | None:
    """Show an arrow-key menu; return the chosen index or None if cancelled."""

    stream = stream or sys.stdout
    index = 0
    _render(title, options, index, stream)
    height = len(options) + 1
    while True:
        key = read_key()
        if key == "up":
            index = (index - 1) % len(options)
        elif key == "down":
            index = (index + 1) % len(options)
        elif key == "enter":
            return index
        elif key == "cancel":
            return None
        else:
            continue
        stream.write(f"\x1b[{height}A")  # move cursor back up to redraw in place
        _render(title, options, index, stream)
