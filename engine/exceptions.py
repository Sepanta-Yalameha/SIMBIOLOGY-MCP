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


class SbioError(Exception):
    """Base error for the SimBiology core layer."""


class ProjectNotLoadedError(SbioError):
    """Raised when a session or model operation runs before a project is loaded."""


class ModelNotFoundError(SbioError):
    """Raised when a requested model name is missing or ambiguous."""


class ElementNotFoundError(SbioError):
    """Raised when a named species/reaction/compartment/parameter does not exist."""


class AutosaveError(SbioError):
    """Raised when a mutation succeeds in memory but writing the recovery project fails."""
