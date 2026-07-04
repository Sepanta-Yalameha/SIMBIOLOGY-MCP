"""FastMCP server wiring for SimBiology tools."""

from __future__ import annotations

import sys
from fastmcp import FastMCP

from tools import TOOLS


def build_server() -> FastMCP:
    """Create and configure the FastMCP server."""

    mcp = FastMCP()
    for tool_fn in TOOLS.values():
        mcp.add_tool(tool_fn)
    return mcp


def run() -> None:
    """Console-script entry point: build the server and serve it."""

    try:
        import matlab.engine
    except ImportError:
        print(
            "MATLAB Engine for Python is not installed.\nRun `simbiology-mcp-setup` to install it from your local MATLAB installation.",
            file=sys.stderr,
        )
    sys.exit(1)

    build_server().run()
