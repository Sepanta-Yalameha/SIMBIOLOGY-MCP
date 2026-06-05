import pytest

from engine.exceptions import (
    MatlabCommandFailedError,
    MatlabCommandNotFoundError,
    MatlabNotAliveError,
    MatlabNotRunningError,
)
from engine.matlab_layer import MatlabLayer


class FakeEngine:
    def __init__(self):
        self.calls = []
        self.quit_called = False
        self.probe_result = None
        self.probe_side_effect = None
        self.eval_result = None
        self.eval_side_effect = None

    def eval(self, command, nargout=0):
        self.calls.append((command, nargout))
        if command == "1+1;":
            if self.probe_side_effect is not None:
                raise self.probe_side_effect
            return self.probe_result
        if self.eval_side_effect is not None:
            raise self.eval_side_effect
        return self.eval_result

    def quit(self):
        self.quit_called = True


@pytest.fixture(autouse=True)
def reset_layer():
    MatlabLayer._eng = None


def test_launch_returns_single_engine(monkeypatch):
    fake = FakeEngine()
    monkeypatch.setattr("matlab.engine.start_matlab", lambda: fake)

    eng1 = MatlabLayer.launch()
    eng2 = MatlabLayer.launch()

    assert eng1 is fake
    assert eng2 is fake


def test_execute_returns_result(monkeypatch):
    fake = FakeEngine()
    fake.eval_result = 2
    monkeypatch.setattr("matlab.engine.start_matlab", lambda: fake)

    MatlabLayer.launch()
    result = MatlabLayer.execute("1 + 1", nargout=1)

    assert result == 2
    assert fake.calls == [("1+1;", 0), ("1 + 1", 1)]


def test_execute_maps_missing_command_to_not_found(monkeypatch):
    fake = FakeEngine()
    fake.eval_side_effect = SyntaxError("invalid syntax")
    monkeypatch.setattr("matlab.engine.start_matlab", lambda: fake)

    MatlabLayer.launch()

    with pytest.raises(MatlabCommandNotFoundError):
        MatlabLayer.execute("bad command", nargout=0)
    assert fake.calls == [("1+1;", 0), ("bad command", 0)]


def test_execute_maps_runtime_failure(monkeypatch):
    fake = FakeEngine()
    fake.eval_side_effect = RuntimeError("division by zero")
    monkeypatch.setattr("matlab.engine.start_matlab", lambda: fake)

    MatlabLayer.launch()

    with pytest.raises(MatlabCommandFailedError):
        MatlabLayer.execute("1/0", nargout=0)
    assert fake.calls == [("1+1;", 0), ("1/0", 0)]


def test_execute_raises_when_engine_is_not_alive(monkeypatch):
    fake = FakeEngine()
    fake.probe_side_effect = RuntimeError("terminated")
    monkeypatch.setattr("matlab.engine.start_matlab", lambda: fake)

    MatlabLayer.launch()

    with pytest.raises(MatlabNotAliveError):
        MatlabLayer.execute("1 + 1", nargout=0)
    assert fake.calls == [("1+1;", 0)]


def test_ensure_alive_returns_true_when_eval_succeeds(monkeypatch):
    fake = FakeEngine()
    monkeypatch.setattr("matlab.engine.start_matlab", lambda: fake)

    MatlabLayer.launch()

    assert MatlabLayer.ensure_alive()
    assert fake.calls == [("1+1;", 0)]


def test_ensure_alive_raises_when_engine_missing():
    with pytest.raises(MatlabNotAliveError):
        MatlabLayer.ensure_alive()


def test_exit_quits_engine(monkeypatch):
    fake = FakeEngine()
    monkeypatch.setattr("matlab.engine.start_matlab", lambda: fake)

    MatlabLayer.launch()
    MatlabLayer.exit()

    assert fake.quit_called
    assert MatlabLayer._eng is None


def test_ensure_alive_raises_when_dead(monkeypatch):
    fake = FakeEngine()
    fake.probe_side_effect = RuntimeError("terminated")
    monkeypatch.setattr("matlab.engine.start_matlab", lambda: fake)

    MatlabLayer.launch()

    with pytest.raises(MatlabNotAliveError):
        MatlabLayer.ensure_alive()
