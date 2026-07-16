import pytest

from simbiology_mcp.engine.exceptions import (
    MatlabCommandFailedError,
    MatlabCommandNotFoundError,
    MatlabNotAliveError,
    MatlabNotRunningError,
)
from simbiology_mcp.engine.matlab_layer import MatlabLayer


class FakeMatlabExecutionError(Exception):
    """Test double for matlab.engine.MatlabExecutionError."""


class FakeEngine:
    def __init__(self) -> None:
        self.calls: list[tuple[str, int]] = []
        self.quit_called = False
        self.probe_error: Exception | None = None
        self.eval_error: Exception | None = None
        self.result = None

    def eval(self, command: str, nargout: int = 0):
        self.calls.append((command, nargout))
        if command == "1+1;":
            if self.probe_error is not None:
                raise self.probe_error
            return None
        if self.eval_error is not None:
            raise self.eval_error
        return self.result

    def quit(self) -> None:
        self.quit_called = True


@pytest.fixture(autouse=True)
def reset_layer():
    MatlabLayer._instance = None
    MatlabLayer._eng = None
    yield
    MatlabLayer._instance = None
    MatlabLayer._eng = None


def test_launch_starts_engine_once(monkeypatch):
    fake = FakeEngine()
    monkeypatch.setattr("simbiology_mcp.engine.matlab_layer._start_matlab", lambda: fake)

    layer = MatlabLayer()
    layer.launch()
    layer.launch()

    assert layer._eng is fake
    assert fake.calls == []


def test_execute_returns_result(monkeypatch):
    fake = FakeEngine()
    fake.result = 2
    monkeypatch.setattr("simbiology_mcp.engine.matlab_layer._start_matlab", lambda: fake)

    layer = MatlabLayer()
    layer.launch()

    assert layer.execute("1 + 1", nargout=1) == 2
    assert fake.calls == [("1+1;", 0), ("1 + 1", 1)]


def test_execute_maps_syntax_error_to_not_found(monkeypatch):
    fake = FakeEngine()
    fake.eval_error = SyntaxError("invalid syntax")
    monkeypatch.setattr("simbiology_mcp.engine.matlab_layer._start_matlab", lambda: fake)

    layer = MatlabLayer()
    layer.launch()

    with pytest.raises(MatlabCommandNotFoundError):
        layer.execute("bad command")


def test_execute_maps_missing_command_text_to_not_found(monkeypatch):
    fake = FakeEngine()
    fake.eval_error = FakeMatlabExecutionError("Undefined function or variable 'x'")
    monkeypatch.setattr("simbiology_mcp.engine.matlab_layer._start_matlab", lambda: fake)
    monkeypatch.setattr("simbiology_mcp.engine.matlab_layer.MatlabExecutionError", FakeMatlabExecutionError)

    layer = MatlabLayer()
    layer.launch()

    with pytest.raises(MatlabCommandNotFoundError):
        layer.execute("x")


def test_execute_maps_runtime_error_to_failed(monkeypatch):
    fake = FakeEngine()
    fake.eval_error = FakeMatlabExecutionError("division by zero")
    monkeypatch.setattr("simbiology_mcp.engine.matlab_layer._start_matlab", lambda: fake)
    monkeypatch.setattr("simbiology_mcp.engine.matlab_layer.MatlabExecutionError", FakeMatlabExecutionError)

    layer = MatlabLayer()
    layer.launch()

    with pytest.raises(MatlabCommandFailedError):
        layer.execute("1/0")


def test_execute_raises_when_engine_not_alive(monkeypatch):
    fake = FakeEngine()
    fake.probe_error = RuntimeError("terminated")
    monkeypatch.setattr("simbiology_mcp.engine.matlab_layer._start_matlab", lambda: fake)

    layer = MatlabLayer()
    layer.launch()

    with pytest.raises(MatlabNotAliveError):
        layer.execute("1 + 1")


def test_ensure_alive_requires_launch():
    layer = MatlabLayer()

    with pytest.raises(MatlabNotRunningError):
        layer.ensure_alive()


def test_ensure_alive_detects_dead_engine(monkeypatch):
    fake = FakeEngine()
    fake.probe_error = RuntimeError("terminated")
    monkeypatch.setattr("simbiology_mcp.engine.matlab_layer._start_matlab", lambda: fake)

    layer = MatlabLayer()
    layer.launch()

    with pytest.raises(MatlabNotAliveError):
        layer.ensure_alive()


def test_exit_quits_engine(monkeypatch):
    fake = FakeEngine()
    monkeypatch.setattr("simbiology_mcp.engine.matlab_layer._start_matlab", lambda: fake)

    layer = MatlabLayer()
    layer.launch()
    layer.exit()

    assert fake.quit_called
    assert layer._eng is None

