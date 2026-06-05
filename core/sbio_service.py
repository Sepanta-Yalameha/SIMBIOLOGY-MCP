"""The SimBiology session: load/save a .sbproj, discover and hand out models.

Routes every MATLAB call through the singleton MatlabLayer (never imports
matlab.engine directly), preserving the one-engine guarantee.
"""
from engine.matlab_layer import MatlabLayer
from engine.exceptions import ProjectNotLoadedError, ModelNotFoundError
from core.sbio_model import SbioModel, _ml_str


class SbioService:
    def __init__(self):
        MatlabLayer.launch()
        self.project_path = None
        self._models = {}   # model name -> MATLAB workspace var

    def load_project(self, path):
        """Load a .sbproj, return the names of the models it contains."""
        self.execute("sbioreset;")                       # clean session
        try:
            self.execute(f"sbioloadproject({_ml_str(path)})")
        except RuntimeError as exc:                       # bad/corrupt path
            raise ProjectNotLoadedError(
                f"Could not load project {path!r}: {exc}") from exc
        count = int(self.execute("numel(sbioroot().Models)", nargout=1))
        self._models = {}
        for i in range(1, count + 1):
            var = f"sbio_model_{i}"
            self.execute(f"{var} = sbioroot().Models({i});")
            name = self.execute(f"{var}.Name", nargout=1)
            self._models[str(name)] = var
        self.project_path = path
        return list(self._models.keys())

    def save_project(self, path=None):
        """Persist the loaded models. Defaults to the loaded path (overwrite)."""
        target = path or self.project_path
        if target is None:
            raise ProjectNotLoadedError("No project loaded; nothing to save.")
        var_args = "".join(f",'{v}'" for v in self._models.values())
        self.execute(f"sbiosaveproject({_ml_str(target)}{var_args})")

    def model_names(self):
        return list(self._models.keys())

    def get_model(self, name=None):
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

    def execute(self, command, nargout=0):
        """Run a model-scoped MATLAB command through the engine."""
        return MatlabLayer.execute(command, nargout)
