"""Top-level CLI for simbiology-mcp."""

from __future__ import annotations

import argparse

from scripts import get_skill, setup


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="simbiology-mcp")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("start", help="Start the SimBiology MCP server.")

    get_skill_parser = subparsers.add_parser("get-skill", help="Install or print the packaged skill (interactive picker with no flags).")
    get_skill_parser.add_argument("--print", action="store_true", dest="print_skill", help="Print SKILL.md to stdout.")
    get_skill_parser.add_argument("--install", action="store_true", help="Install SKILL.md into a client's skills directory (pass --client to skip the picker).")
    get_skill_parser.add_argument("--client", choices=sorted(get_skill._CLIENT_SKILL_DIRS), help="Client to install for. Omit with --install to pick from the interactive menu.")
    get_skill_scope = get_skill_parser.add_mutually_exclusive_group()
    get_skill_scope.add_argument("--user", action="store_true", help="Install into the user-level skills directory (default).")
    get_skill_scope.add_argument("--project", action="store_true", help="Install into the current project's skills directory.")
    get_skill_parser.add_argument("--install-path", help="Install to an explicit path instead of a client skills directory.")

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
        get_skill.main(_get_skill_argv(args))
        return

    if args.command == "setup":
        setup.main(_setup_argv(args))
        return

    parser.error(f"Unknown command: {args.command}")


def _get_skill_argv(args: argparse.Namespace) -> list[str]:
    argv: list[str] = []
    if args.print_skill:
        argv.append("--print")
    if args.install:
        argv.append("--install")
    if args.client is not None:
        argv.extend(["--client", args.client])
    if args.project:
        argv.append("--project")
    elif args.user:
        argv.append("--user")
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
