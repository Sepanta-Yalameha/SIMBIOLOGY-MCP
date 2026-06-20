"""The SimBiology session.

Loads and saves a project (.sbproj), discovers its models, and hands out
SbioModel gateways. Every MATLAB call is routed through the singleton
MatlabLayer, never through matlab.engine directly.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from engine.matlab_layer import MatlabLayer
from engine.exceptions import MatlabError, ProjectNotLoadedError, ModelNotFoundError
from core.sbio_model import SbioModel, to_matlab_string


class SbioService:
    """Owns one SimBiology session over the shared MATLAB engine."""

    def __init__(self) -> None:
        MatlabLayer().launch()
        self.project_path: str | None = None
        self._models: dict[str, str] = {}

    def load_project(self, path: str) -> list[str]:
        self._reset()
        try:
            self.execute(f"sbioloadproject({to_matlab_string(path)})")
        except MatlabError as exc:
            raise ProjectNotLoadedError(f"Could not load project {path!r}: {exc}") from exc
        self._models = self._load_models()
        self.project_path = path
        return self.model_names()

    def create_project(self, model_name: str, path: str | None = None) -> list[str]:
        """Create a fresh project with one model."""

        self._reset()
        self.execute(f"m = sbiomodel({to_matlab_string(model_name)});")
        self._models = {model_name: "m"}
        self.project_path = path
        if path is not None:
            self.save_project(path)
        return self.model_names()

    def save_project(self, path: str | None = None) -> None:
        target = self._target_path(path)
        Path(target).parent.mkdir(parents=True, exist_ok=True)
        self.execute(f"sbiosaveproject({to_matlab_string(target)}{self._model_args()})")

    def create_model(self, name: str) -> SbioModel:
        """Create a model in the current project and return it."""

        if not self._models:
            raise ProjectNotLoadedError("No project loaded.")
        var = f"sbio_model_{len(self._models) + 1}"
        self.execute(f"{var} = sbiomodel({to_matlab_string(name)});")
        self._models[name] = var
        return SbioModel(self, var, name)

    def delete_model(self, name: str) -> None:
        """Delete a model from the current project."""

        model = self._get_model(name)
        self.execute(model.delete_model_cmd())
        self._models.pop(model.name, None)

    def rename_model(self, old_name: str, new_name: str) -> SbioModel:
        """Rename a model in the current project."""

        model = self._get_model(old_name)
        self.execute(model.rename_model_cmd(new_name))
        self._models.pop(old_name)
        self._models[new_name] = model.var
        model.name = new_name
        return model

    def model_names(self) -> list[str]:
        """Return the names of the loaded models."""

        return list(self._models.keys())

    def get_model(self, name: str | None = None) -> SbioModel:
        if not self._models:
            raise ProjectNotLoadedError("No project loaded.")
        if name is None:
            if len(self._models) != 1:
                raise ModelNotFoundError(f"Specify a model name; loaded: {list(self._models)}")
            name = next(iter(self._models))
        return self._get_model(name)

    def execute(self, command: str, nargout: int = 0) -> Any:
        """Run a MATLAB command through the shared engine."""

        return MatlabLayer().execute(command, nargout)

    def _reset(self) -> None:
        self.execute("sbioreset;")

    def _target_path(self, path: str | None) -> str:
        target = path or self.project_path
        if target is None:
            raise ProjectNotLoadedError("No project loaded; nothing to save.")
        return target

    def _model_args(self) -> str:
        return "".join(f",'{var}'" for var in self._models.values())

    def _load_models(self) -> dict[str, str]:
        count = int(self.execute("numel(sbioroot().Models)", nargout=1))
        models: dict[str, str] = {}
        for index in range(1, count + 1):
            var = f"sbio_model_{index}"
            self.execute(f"{var} = sbioroot().Models({index});")
            models[str(self.execute(f"{var}.Name", nargout=1))] = var
        return models

    def _get_model(self, name: str) -> SbioModel:
        try:
            var = self._models[name]
        except KeyError as exc:
            raise ModelNotFoundError(f"No model named {name!r}; loaded: {list(self._models)}") from exc
        return SbioModel(self, var, name)
