#!/usr/bin/env python3
"""Start the FastMCP Brave Search server."""

import asyncio
import os
import sys
from pathlib import Path

# Add the parent directory to the path so we can import the MCP server
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp.brave_search_server import mcp


async def main():
    """Start the FastMCP Brave Search server."""
    print("Starting FastMCP Brave Search server...")
    
    # Check for Brave API key
    api_key = os.getenv("BRAVE_SEARCH_API_KEY")
    if not api_key:
        print("Warning: BRAVE_SEARCH_API_KEY not found in environment")
        print("Please set your Brave Search API key:")
        print("export BRAVE_SEARCH_API_KEY=your_api_key_here")
        return
    
    print(f"Brave API key configured: {api_key[:8]}...")
    
    # Start the server
    try:
        print("FastMCP Brave Search server starting on port 8000...")
        print("Server will be available at: http://localhost:8000/mcp")
        mcp.run(port=8000)
    except KeyboardInterrupt:
        print("\nServer stopped by user")
    except Exception as e:
        print(f"Server error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
