"""Smoke test: MCP server module imports cleanly."""

from mcp.server.fastmcp import FastMCP

import adapters.mcp.server


def test_mcp_server_imports() -> None:
    """adapters.mcp.server must import without error and expose a FastMCP instance."""
    assert isinstance(adapters.mcp.server.mcp, FastMCP)
