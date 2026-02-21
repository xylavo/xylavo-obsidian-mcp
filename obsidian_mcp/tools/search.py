"""검색 도구."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from obsidian_mcp.vault import ObsidianVault


def register(mcp: FastMCP, vault: ObsidianVault) -> None:
    """검색 도구를 MCP 서버에 등록한다."""

    @mcp.tool()
    async def search_notes(query: str) -> list[dict]:
        """Vault 내 노트를 전문 검색합니다.

        Args:
            query: 검색어
        """
        return vault.search_notes(query)

    @mcp.tool()
    async def search_by_tag(tag: str) -> list[str]:
        """특정 태그가 달린 노트 목록을 검색합니다.

        Args:
            tag: 검색할 태그 (예: "project" 또는 "#project")
        """
        return vault.search_by_tag(tag)
