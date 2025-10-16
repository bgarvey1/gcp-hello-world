#!/usr/bin/env python3
"""MCP server with calculate_sum tool using stdio transport."""

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Calculator Server")


@mcp.tool()
def calculate_sum(a: float, b: float) -> float:
    """Add two numbers together.
    
    Args:
        a: The first number
        b: The second number
        
    Returns:
        The sum of a and b
    """
    return a + b


if __name__ == "__main__":
    mcp.run()
