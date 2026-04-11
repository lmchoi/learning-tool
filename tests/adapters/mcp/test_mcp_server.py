"""Smoke test: MCP server module imports cleanly."""

from mcp.server.fastmcp import FastMCP

import learning_tool.adapters.mcp.server


def test_mcp_server_imports() -> None:
    """learning_tool.adapters.mcp.server must import without error and expose a FastMCP instance."""
    assert isinstance(learning_tool.adapters.mcp.server.mcp, FastMCP)
