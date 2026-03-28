"""MCP server entry point.

Runs as a stdio server configured in Claude Desktop's claude_desktop_config.json.
Tools are added in subsequent issues — this is the skeleton only.

Usage:
    uv run python adapters/mcp/server.py
"""

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("learning-tool")

if __name__ == "__main__":
    mcp.run(transport="stdio")
