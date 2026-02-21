"""Obsidian MCP Server 엔트리포인트."""

from obsidian_mcp.server import mcp

def main():
    mcp.run(transport="stdio")

if __name__ == "__main__":
    main()
