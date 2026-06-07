"""Repository-level entry point for the SimBiology MCP server."""

from __future__ import annotations

from interfaces.mcp_server import build_server

if __name__ == "__main__":
    mcp = build_server()
    mcp.run()
