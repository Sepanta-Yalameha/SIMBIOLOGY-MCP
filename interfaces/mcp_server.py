"""FastMCP server wiring for SimBiology tools."""

from __future__ import annotations

from fastmcp import FastMCP

from tools.registry import TOOLS


class MCPServer:
    """Configure and run the FastMCP server."""

    def __init__(self) -> None:
        self.mcp = FastMCP()
        self._register_tools()

    def _register_tools(self) -> None:
        """Register all internal tool classes with FastMCP."""

        for tool_cls in TOOLS.values():
            self.mcp.add_tool(tool_cls)

    def run_server(self) -> None:
        """Run the MCP server."""

        self.mcp.run()


if __name__ == "__main__":
    MCPServer().run_server()
