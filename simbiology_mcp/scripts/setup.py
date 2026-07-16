"""Installs MATLAB Engine for Python into the current environment."""

import argparse
import glob
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


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

    from . import tui

    if not tui.is_interactive():
        listing = "\n".join(f"  [{i}] {version} -> {root}" for i, (version, root) in enumerate(installs))
        sys.exit(f"Multiple MATLAB installations found. Re-run with --matlab-index N:\n{listing}")

    tui.enable_windows_ansi()
    options = [f"{version}   ({root})" for version, root in installs]
    choice = tui.select("Select your MATLAB installation  (up/down to move, Enter to select, q to cancel)", options)
    if choice is None:
        sys.exit("No MATLAB installation selected.")
    return installs[choice][1]


def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--matlab-root")
    parser.add_argument("--matlab-index", type=int)
    args = parser.parse_args(argv)

    matlab_root = select_matlab_root(args.matlab_root, args.matlab_index)
    engine_dir = matlab_root / "extern" / "engines" / "python"
    if not engine_dir.exists():
        sys.exit(f"MATLAB engine path not found: {engine_dir}")

    build_temp = Path(tempfile.gettempdir()) / "matlab_engine_build"
    shutil.rmtree(build_temp, ignore_errors=True)
    build_temp.mkdir(parents=True)

    # uv can install prebuilt wheels (setuptools, wheel) without needing pip
    # present in the target venv at all.
    subprocess.run(
        ["uv", "pip", "install", "--python", sys.executable, "setuptools", "wheel"],
        check=True,
    )

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

    # Offer to install the workflow skill into an agent's skills directory.
    from . import get_skill

    get_skill.interactive_install(fallback="hint")


if __name__ == "__main__":
    main()
