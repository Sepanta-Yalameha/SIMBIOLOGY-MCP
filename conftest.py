"""Project-wide pytest configuration: integration/live test gating.

Markers
-------
- ``matlab``: needs a live MATLAB Engine; auto-skipped when MATLAB is not importable.
- ``live``:   calls an external network API; runs only with ``--run-live``.

CI runs ``pytest -m "not matlab and not live"`` to stay fast and hermetic; the
full suite runs locally where MATLAB and network access are available.
"""

from __future__ import annotations

import importlib.util
import pytest


def matlab_available() -> bool:
    """True when the MATLAB Engine for Python can be imported."""

    return importlib.util.find_spec("matlab") is not None


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "matlab: requires a live MATLAB Engine")
    config.addinivalue_line("markers", "live: calls an external network API (opt-in via --run-live)")


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--run-live",
        action="store_true",
        default=False,
        help="run tests marked 'live' that call external network APIs",
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    skip_matlab = pytest.mark.skip(reason="MATLAB Engine not available")
    skip_live = pytest.mark.skip(reason="needs --run-live (external network API)")
    run_live = config.getoption("--run-live")
    has_matlab = matlab_available()
    for item in items:
        if "matlab" in item.keywords and not has_matlab:
            item.add_marker(skip_matlab)
        if "live" in item.keywords and not run_live:
            item.add_marker(skip_live)
