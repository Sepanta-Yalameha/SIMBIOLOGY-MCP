"""Thin MATLAB engine wrapper used by the core SimBiology service."""

from __future__ import annotations

from typing import Any

from engine.exceptions import (
    MatlabCommandNotFoundError,
    MatlabCommandFailedError,
    MatlabNotAliveError,
    MatlabNotRunningError,
)

try:  # The MATLAB Engine for Python is optional at import time (CI, linting).
    from matlab.engine import MatlabExecutionError
except ImportError:  # Real calls fail later in launch(); module import stays safe.

    class MatlabExecutionError(Exception):
        """Fallback when the MATLAB Engine for Python is not installed."""


def _start_matlab() -> Any:
    """Start and return a MATLAB engine.

    Imported lazily so this module loads on machines without the MATLAB Engine
    for Python (CI, static analysis); patched directly in unit tests.
    """

    import matlab.engine

    return matlab.engine.start_matlab()


class MatlabLayer:
    """Singleton wrapper around the MATLAB engine."""

    _instance: MatlabLayer | None = None

    def __new__(cls) -> MatlabLayer:
        """Create or return the singleton MATLAB layer instance."""

        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._eng = None
        return cls._instance

    def launch(self) -> None:
        """Start MATLAB if it is not already running."""

        if self._eng is None:
            self._eng = _start_matlab()

    def execute(self, command: str, nargout: int = 0) -> Any:
        """Execute a MATLAB command.

        Args:
            command: MATLAB command string to evaluate.
            nargout: Number of expected output arguments.

        Returns:
            The result returned by the MATLAB engine.

        Raises:
            MatlabNotRunningError: If MATLAB has not been launched.
            MatlabNotAliveError: If the engine is no longer responsive.
            MatlabCommandNotFoundError: If MATLAB cannot resolve the command.
            MatlabCommandFailedError: If MATLAB raises a runtime error.
        """

        self.ensure_alive()
        try:
            return self._eng.eval(command, nargout=nargout)
        except SyntaxError as exc:
            raise MatlabCommandNotFoundError(f"MATLAB command not found: {command}") from exc
        except MatlabExecutionError as exc:
            message = str(exc)
            missing_markers = (
                "Undefined function or variable",
                "Unrecognized function or variable",
                "Unable to resolve the name",
                "not found",
            )
            if any(marker in message for marker in missing_markers):
                raise MatlabCommandNotFoundError(f"MATLAB command not found: {command}\nMATLAB error: {message}") from exc
            raise MatlabCommandFailedError(f"MATLAB command failed: {command}\nMATLAB error: {message}") from exc
        except Exception as exc:
            raise MatlabCommandFailedError(f"MATLAB command failed: {command}\nPython error: {exc}") from exc

    def ensure_alive(self) -> None:
        """Verify that the MATLAB engine is responsive.

        Raises:
            MatlabNotRunningError: If MATLAB has not been launched.
            MatlabNotAliveError: If the running engine fails a probe call.
        """

        if self._eng is None:
            raise MatlabNotRunningError("MATLAB is not running. Start it by calling MatlabLayer.launch().")
        try:
            self._eng.eval("1+1;", nargout=0)
        except Exception as exc:
            raise MatlabNotAliveError("MATLAB engine is not alive.") from exc

    def exit(self) -> None:
        """Stop the MATLAB engine and clear the cached instance."""

        if self._eng is not None:
            self._eng.quit()
            self._eng = None
