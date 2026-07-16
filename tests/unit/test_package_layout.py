from __future__ import annotations

from importlib import util


def test_namespace_package_layout():
    assert util.find_spec("simbiology_mcp") is not None
    assert util.find_spec("simbiology_mcp.core") is not None
    assert util.find_spec("simbiology_mcp.engine") is not None
    assert util.find_spec("simbiology_mcp.interfaces") is not None
    assert util.find_spec("simbiology_mcp.tools") is not None
    assert util.find_spec("core") is None
    assert util.find_spec("interfaces") is None
    assert util.find_spec("tools") is None
