"""Installs MATLAB Engine for Python into the current environment."""

import argparse
import glob
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from . import configure_mcp, get_skill, tui


def find_matlab_installs_windows():
    import winreg

    installs = []
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\MathWorks\MATLAB") as key:
            i = 0
            while True:
                try:
                    version = winreg.EnumKey(key, i)
                except OSError:
                    break
                i += 1
                with winreg.OpenKey(key, version) as vkey:
                    root, _ = winreg.QueryValueEx(vkey, "MATLABROOT")
                    installs.append((version, Path(root)))
    except FileNotFoundError:
        pass
    return sorted(installs, reverse=True)


def find_matlab_installs_macos():
    paths = sorted(glob.glob("/Applications/MATLAB_R*.app"), reverse=True)
    return [(Path(p).stem, Path(p)) for p in paths]


def find_matlab_installs_linux():
    paths = sorted(glob.glob("/usr/local/MATLAB/R*"), reverse=True)
    paths += sorted(glob.glob("/opt/MATLAB/R*"), reverse=True)
    return [(Path(p).name, Path(p)) for p in paths]


def find_matlab_installs():
    if sys.platform == "win32":
        return find_matlab_installs_windows()
    if sys.platform == "darwin":
        return find_matlab_installs_macos()
    if sys.platform.startswith("linux"):
        return find_matlab_installs_linux()
    sys.exit("Unsupported platform. Pass --matlab-root explicitly.")


def select_matlab_root(root_arg, index_arg):
    if root_arg:
        return Path(root_arg)

    installs = find_matlab_installs()
    if not installs:
        sys.exit("No MATLAB installation found. Pass --matlab-root explicitly.")

    if index_arg is not None:
        if not 0 <= index_arg < len(installs):
            sys.exit(f"--matlab-index {index_arg} is out of range ({len(installs)} installations found).")
        return installs[index_arg][1]

    if len(installs) == 1:
        return installs[0][1]

    if not tui.is_interactive():
        listing = "\n".join(f"  [{i}] {version} -> {root}" for i, (version, root) in enumerate(installs))
        sys.exit(f"Multiple MATLAB installations found. Re-run with --matlab-index N:\n{listing}")

    tui.enable_windows_ansi()
    options = [f"{version}   ({root})" for version, root in installs]
    choice = tui.select("Select your MATLAB installation  (up/down to move, Enter to select, q to cancel)", options)
    if choice is None:
        sys.exit("No MATLAB installation selected.")
    return installs[choice][1]


def _install_build_deps() -> None:
    """Install the wheels matlabengine's setup.py needs to build (setuptools, wheel).

    uv is preferred because it can install prebuilt wheels without pip present in
    the target venv at all. But the README's plain-`pip` install path promises
    `setup` works for people who do not want uv, so uv must not be a hard
    requirement: with no uv, bootstrap pip via ensurepip and use it instead.
    """
    uv_available = shutil.which("uv") is not None
    if uv_available:
        command = ["uv", "pip", "install", "--python", sys.executable, "setuptools", "wheel"]
    else:
        # ensurepip is a no-op when pip is already present and bootstraps it when
        # it is not; either way the install below then has a pip to run.
        subprocess.run([sys.executable, "-m", "ensurepip", "--upgrade"], check=False)
        command = [sys.executable, "-m", "pip", "install", "setuptools", "wheel"]
    if subprocess.run(command).returncode != 0:
        sys.exit("Failed to install build dependencies (setuptools, wheel). Install them manually, then re-run.")


def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--matlab-root")
    parser.add_argument("--matlab-index", type=int)
    parser.add_argument("--client", choices=configure_mcp.client_names())
    scope = parser.add_mutually_exclusive_group()
    scope.add_argument("--user", action="store_true")
    scope.add_argument("--project", action="store_true")
    parser.add_argument("--skip-configure", action="store_true")
    parser.add_argument("--no-skill", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    if args.skip_configure and (args.client is not None or args.user or args.project):
        parser.error("--skip-configure cannot be combined with --client, --user, or --project")

    matlab_root = select_matlab_root(args.matlab_root, args.matlab_index)
    engine_dir = matlab_root / "extern" / "engines" / "python"
    if not engine_dir.exists():
        sys.exit(f"MATLAB engine path not found: {engine_dir}")

    build_temp = Path(tempfile.gettempdir()) / "matlab_engine_build"
    shutil.rmtree(build_temp, ignore_errors=True)
    build_temp.mkdir(parents=True)

    _install_build_deps()

    # Build IN PLACE inside the real MATLAB folder (matlabengine's setup.py
    # validates the install via paths relative to its own location, so it
    # can't be copied elsewhere first). Only the build/egg-info/record
    # artifacts are redirected to TEMP, since Program Files isn't writable
    # without admin.
    result = subprocess.run(
        [sys.executable, "setup.py", "build", "--build-base", str(build_temp), "egg_info", "--egg-base", str(build_temp), "install", "--record", str(build_temp / "record.txt")],
        cwd=engine_dir,
    )
    if result.returncode != 0:
        sys.exit(f"Install failed (exit {result.returncode}).")

    print("matlabengine installed successfully.")

    if args.skip_configure:
        return

    scope_name = "project" if args.project else "user"
    if args.client is not None:
        status = configure_mcp.configure_client(args.client, scope=scope_name, force=args.force, dry_run=args.dry_run)
        if not args.no_skill and not args.dry_run and status != configure_mcp.CANCELLED:
            get_skill._install_for_client(args.client, scope_name)
        return

    configured = configure_mcp.interactive_configure(
        preferred_scope="project" if args.project else None,
        force=args.force,
        dry_run=args.dry_run,
        noninteractive_fallback="hint",
    )
    if configured is not None and not args.no_skill and not args.dry_run:
        get_skill.interactive_install_after_configure(*configured)


if __name__ == "__main__":
    main()
