"""Top-level CLI for simbiology-mcp."""

from __future__ import annotations

import argparse

from ..scripts import configure_mcp, get_skill, setup


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="simbiology-mcp")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("start", help="Start the SimBiology MCP server.")

    get_skill_parser = subparsers.add_parser("get-skill", help="Print or install the packaged skill (interactive picker with no flags).")
    get_skill_mode = get_skill_parser.add_mutually_exclusive_group()
    get_skill_mode.add_argument("--print", action="store_true", dest="print_skill", help="Print SKILL.md to stdout.")
    get_skill_mode.add_argument("--client", choices=sorted(get_skill.client_names()), help="Install directly for a client. Combine with --user or --project to choose scope.")
    get_skill_mode.add_argument("--install-path", help="Install directly to an explicit path.")
    get_skill_scope = get_skill_parser.add_mutually_exclusive_group()
    get_skill_scope.add_argument("--user", action="store_true", help="Install into the user-level skills directory (default).")
    get_skill_scope.add_argument("--project", action="store_true", help="Install into the current project's skills directory.")

    configure_parser = subparsers.add_parser("configure", help="Configure an MCP client for the SimBiology server.")
    configure_parser.add_argument("--client", choices=configure_mcp.client_names())
    configure_scope = configure_parser.add_mutually_exclusive_group()
    configure_scope.add_argument("--user", action="store_true", help="Configure the user scope (default).")
    configure_scope.add_argument("--project", action="store_true", help="Configure the project scope.")
    configure_parser.add_argument("--force", action="store_true", help="Replace an existing entry without prompting.")
    configure_parser.add_argument("--dry-run", action="store_true", help="Print the generated configuration without writing it.")
    configure_parser.add_argument("--list-clients", action="store_true", help="List supported MCP clients.")

    setup_parser = subparsers.add_parser("setup", help="Install MATLAB Engine for Python from a local MATLAB installation.")
    setup_parser.add_argument("--matlab-root")
    setup_parser.add_argument("--matlab-index", type=int)
    setup_client = setup_parser.add_mutually_exclusive_group()
    setup_client.add_argument("--client", choices=configure_mcp.client_names())
    setup_scope = setup_parser.add_mutually_exclusive_group()
    setup_scope.add_argument("--user", action="store_true", help="Configure the user scope after install (default).")
    setup_scope.add_argument("--project", action="store_true", help="Configure the project scope after install.")
    setup_parser.add_argument("--skip-configure", action="store_true", help="Install MATLAB Engine only.")
    setup_parser.add_argument("--no-skill", action="store_true", help="Do not install the SimBiology skill after MCP setup.")
    setup_parser.add_argument("--force", action="store_true", help="Replace an existing entry without prompting.")
    setup_parser.add_argument("--dry-run", action="store_true", help="Print the generated configuration without writing it.")

    return parser


def _run_server() -> None:
    from .mcp_server import run as run_server

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

    if args.command == "configure":
        configure_mcp.main(_configure_argv(args))
        return

    if args.command == "setup":
        setup.main(_setup_argv(args))
        return

    parser.error(f"Unknown command: {args.command}")


def _get_skill_argv(args: argparse.Namespace) -> list[str]:
    argv: list[str] = []
    if args.print_skill:
        argv.append("--print")
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
    if args.client is not None:
        argv.extend(["--client", args.client])
    if args.project:
        argv.append("--project")
    elif args.user:
        argv.append("--user")
    if args.skip_configure:
        argv.append("--skip-configure")
    if args.no_skill:
        argv.append("--no-skill")
    if args.force:
        argv.append("--force")
    if args.dry_run:
        argv.append("--dry-run")
    return argv


def _configure_argv(args: argparse.Namespace) -> list[str]:
    argv: list[str] = []
    if args.client is not None:
        argv.extend(["--client", args.client])
    if args.project:
        argv.append("--project")
    elif args.user:
        argv.append("--user")
    if args.force:
        argv.append("--force")
    if args.dry_run:
        argv.append("--dry-run")
    if args.list_clients:
        argv.append("--list-clients")
    return argv


if __name__ == "__main__":
    main()
