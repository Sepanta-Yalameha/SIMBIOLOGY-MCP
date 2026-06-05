"""Custom error types for the SimBiology core layer.

Core raises these for precondition failures *before* touching MATLAB. Genuine
MATLAB failures keep propagating from MatlabLayer as RuntimeError.
"""


class SbioError(Exception):
    """Base class for all errors raised by the SimBiology core layer."""


class ProjectNotLoadedError(SbioError):
    """A session or model operation ran before a project was loaded."""


class ModelNotFoundError(SbioError):
    """A requested model name is missing, or get_model(None) is ambiguous."""


class ElementNotFoundError(SbioError):
    """A named species/reaction/compartment/parameter does not exist."""
