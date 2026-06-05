"""Thin MATLAB engine wrapper used by the core SimBiology service."""

from __future__ import annotations

import matlab.engine
from matlab.engine import MatlabExecutionError

from engine.exceptions import (
    MatlabCommandNotFoundError,
    MatlabCommandFailedError,
    MatlabNotAliveError,
    MatlabNotRunningError,
)


class MatlabLayer:
    _eng = None

    @classmethod
    def launch(cls):
        if cls._eng is None:
            cls._eng = matlab.engine.start_matlab()
        return cls._eng

    @classmethod
    def execute(cls, command, nargout=0):
        cls.ensure_alive()
        try:
            return cls._eng.eval(command, nargout=nargout)
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
                raise MatlabCommandNotFoundError(f"MATLAB command not found: {command}") from exc
            raise MatlabCommandFailedError(f"MATLAB command failed: {command}") from exc
        except Exception as exc:
            raise MatlabCommandFailedError(f"MATLAB command failed: {command}") from exc

    @classmethod
    def ensure_alive(cls):
        if cls._eng is None:
            raise MatlabNotAliveError("MATLAB engine is not alive.")
        try:
            cls._eng.eval("1+1;", nargout=0)
        except Exception as exc:
            raise MatlabNotAliveError("MATLAB engine is not alive.") from exc
        return True

    @classmethod
    def exit(cls):
        if cls._eng is not None:
            cls._eng.quit()
            cls._eng = None
