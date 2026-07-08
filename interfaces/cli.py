"""Top-level CLI for simbiology-mcp."""

from __future__ import annotations

import argparse

from scripts import get_skill, setup


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="simbiology-mcp")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("start", help="Start the SimBiology MCP server.")

    get_skill_parser = subparsers.add_parser("get-skill", help="Print or copy the packaged skill.")
    get_skill_parser.add_argument("--print", action="store_true", dest="print_skill", help="Print SKILL.md to stdout.")
    get_skill_parser.add_argument("--install-path", help="Write SKILL.md to the given destination path instead of printing it.")

    setup_parser = subparsers.add_parser("setup", help="Install MATLAB Engine for Python from a local MATLAB installation.")
    setup_parser.add_argument("--matlab-root")
    setup_parser.add_argument("--matlab-index", type=int)

    return parser


def _run_server() -> None:
    from interfaces.mcp_server import run as run_server

    run_server()


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return

    if args.command == "start":
        _run_server()
        return

    if args.command == "get-skill":
        get_skill.main(["--print"] if args.print_skill and args.install_path is None else _get_skill_argv(args))
        return

    if args.command == "setup":
        setup.main(_setup_argv(args))
        return

    parser.error(f"Unknown command: {args.command}")


def _get_skill_argv(args: argparse.Namespace) -> list[str]:
    argv: list[str] = []
    if args.print_skill:
        argv.append("--print")
    if args.install_path is not None:
        argv.extend(["--install-path", args.install_path])
    return argv


def _setup_argv(args: argparse.Namespace) -> list[str]:
    argv: list[str] = []
    if args.matlab_root is not None:
        argv.extend(["--matlab-root", args.matlab_root])
    if args.matlab_index is not None:
        argv.extend(["--matlab-index", str(args.matlab_index)])
    return argv


if __name__ == "__main__":
    main()
