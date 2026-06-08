"""The SimBiology session.

Loads and saves a project (.sbproj), discovers its models, and hands out
SbioModel gateways. Every MATLAB call is routed through the singleton
MatlabLayer, never through matlab.engine directly.
"""

from __future__ import annotations

from typing import Any

from engine.matlab_layer import MatlabLayer
from engine.exceptions import MatlabError, ProjectNotLoadedError, ModelNotFoundError
from core.sbio_model import SbioModel, to_matlab_string


class SbioService:
    """Owns one SimBiology session over the shared MATLAB engine."""

    def __init__(self) -> None:
        MatlabLayer().launch()
        self.project_path: str | None = None
        self._models: dict[str, str] = {}   # model name -> MATLAB workspace var

    def load_project(self, path: str) -> list[str]:
        """Load a project file and return the names of its models.

        Args:
            path: Path to the .sbproj file.

        Returns:
            The names of the models the project contains.

        Raises:
            ProjectNotLoadedError: If MATLAB cannot load the file.
        """

        self.execute("sbioreset;")
        try:
            self.execute(f"sbioloadproject({to_matlab_string(path)})")
        except MatlabError as exc:
            raise ProjectNotLoadedError(
                f"Could not load project {path!r}: {exc}") from exc
        count = int(self.execute("numel(sbioroot().Models)", nargout=1))
        self._models = {}
        for index in range(1, count + 1):
            var = f"sbio_model_{index}"
            self.execute(f"{var} = sbioroot().Models({index});")
            name = self.execute(f"{var}.Name", nargout=1)
            self._models[str(name)] = var
        self.project_path = path
        return list(self._models.keys())

    def save_project(self, path: str | None = None) -> None:
        """Save the loaded models, defaulting to the loaded path.

        Args:
            path: Destination .sbproj path. Defaults to the loaded project.

        Raises:
            ProjectNotLoadedError: If no project is loaded and no path is given.
        """

        target = path or self.project_path
        if target is None:
            raise ProjectNotLoadedError("No project loaded; nothing to save.")
        var_args = "".join(f",'{var}'" for var in self._models.values())
        self.execute(f"sbiosaveproject({to_matlab_string(target)}{var_args})")

    def model_names(self) -> list[str]:
        """Return the names of the loaded models."""

        return list(self._models.keys())

    def get_model(self, name: str | None = None) -> SbioModel:
        """Return a gateway to one model.

        Args:
            name: Model name. If omitted, the sole loaded model is used.

        Returns:
            An SbioModel bound to the requested model.

        Raises:
            ProjectNotLoadedError: If no project is loaded.
            ModelNotFoundError: If the name is missing or the choice is ambiguous.
        """

        if not self._models:
            raise ProjectNotLoadedError("No project loaded.")
        if name is None:
            if len(self._models) != 1:
                raise ModelNotFoundError(
                    f"Specify a model name; loaded: {list(self._models)}")
            name = next(iter(self._models))
        if name not in self._models:
            raise ModelNotFoundError(
                f"No model named {name!r}; loaded: {list(self._models)}")
        return SbioModel(self, self._models[name], name)

    def execute(self, command: str, nargout: int = 0) -> Any:
        """Run a MATLAB command through the shared engine."""

        return MatlabLayer().execute(command, nargout)
