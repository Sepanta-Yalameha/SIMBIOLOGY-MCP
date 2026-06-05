"""Contains exceptions for the entire app."""

from __future__ import annotations


class MatlabError(RuntimeError):
    """Base error for MATLAB engine failures."""


class MatlabNotRunningError(MatlabError):
    """Raised when MATLAB is not started."""


class MatlabCommandNotFoundError(MatlabError):
    """Raised when a MATLAB command cannot be executed."""


class MatlabCommandFailedError(MatlabError):
    """Raised when a MATLAB command exists but fails at runtime."""


class MatlabNotAliveError(MatlabError):
    """Raised when the MATLAB session stops responding."""
