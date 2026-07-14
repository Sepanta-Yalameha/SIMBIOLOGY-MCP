from __future__ import annotations

import sys
import types

import pytest

from interfaces import mcp_server


def test_build_server_adds_all_tools(monkeypatch: pytest.MonkeyPatch) -> None:
    added: list[object] = []

    class FakeMCP:
        def add_tool(self, tool) -> None:
            added.append(tool)

    monkeypatch.setattr(mcp_server, "FastMCP", FakeMCP)

    server = mcp_server.build_server()

    assert isinstance(server, FakeMCP)
    assert added == list(mcp_server.TOOLS.values())


def test_run_exits_cleanly_when_matlab_engine_missing(monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    monkeypatch.setitem(sys.modules, "matlab", None)
    monkeypatch.setitem(sys.modules, "matlab.engine", None)

    with pytest.raises(SystemExit, match="1"):
        mcp_server.run()

    assert "MATLAB Engine for Python is not installed." in capsys.readouterr().err


def test_run_starts_server_when_matlab_engine_present(monkeypatch: pytest.MonkeyPatch) -> None:
    matlab = types.ModuleType("matlab")
    engine = types.ModuleType("matlab.engine")
    matlab.engine = engine
    monkeypatch.setitem(sys.modules, "matlab", matlab)
    monkeypatch.setitem(sys.modules, "matlab.engine", engine)

    called: list[str] = []

    class FakeServer:
        def run(self) -> None:
            called.append("run")

    monkeypatch.setattr(mcp_server, "build_server", lambda: FakeServer())

    mcp_server.run()

    assert called == ["run"]
