"""Installs MATLAB Engine for Python into the current environment."""

import argparse
import glob
import subprocess
import sys
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
    if len(installs) == 1:
        return installs[0][1]

    for i, (version, root) in enumerate(installs):
        print(f"[{i}] {version} -> {root}")
    idx = index_arg if index_arg is not None else int(input("Select index: "))
    return installs[idx][1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--matlab-root")
    parser.add_argument("--matlab-index", type=int)
    args = parser.parse_args()

    matlab_root = select_matlab_root(args.matlab_root, args.matlab_index)
    engine_dir = matlab_root / "extern" / "engines" / "python"
    if not engine_dir.exists():
        sys.exit(f"MATLAB engine path not found: {engine_dir}")

    result = subprocess.run(
        ["uv", "pip", "install", "--python", sys.executable, str(engine_dir)],
    )
    if result.returncode != 0:
        sys.exit(f"Install failed (exit {result.returncode}).")

    print("matlabengine installed successfully.")


if __name__ == "__main__":
    main()
