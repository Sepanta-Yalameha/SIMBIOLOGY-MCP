"""Print or copy the packaged SimBiology skill markdown."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _skill_path() -> Path:
    return Path(__file__).with_name("SKILLS.md")


def _skill_text() -> str:
    return _skill_path().read_text(encoding="utf-8")


def _write_skill(path: Path) -> tuple[Path, Path]:
    source = _skill_path().resolve()
    target = path.expanduser().resolve()
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(_skill_text(), encoding="utf-8")
    except PermissionError as exc:
        raise PermissionError(f"Access denied while writing skill to {target}") from exc
    return source, target


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--print", action="store_true", dest="print_skill", help="Print SKILLS.md to stdout.")
    parser.add_argument("--install-path", help="Write SKILLS.md to the given destination path instead of printing it.")
    if len(sys.argv) == 1:
        parser.print_help()
        return
    args = parser.parse_args()

    if not args.print_skill and args.install_path is None:
        parser.print_help()
        return

    if args.print_skill:
        print(_skill_text())

    if args.install_path is not None:
        source, target = _write_skill(Path(args.install_path))
        print(f"Copied skill from {source} to {target}")


if __name__ == "__main__":
    main()
