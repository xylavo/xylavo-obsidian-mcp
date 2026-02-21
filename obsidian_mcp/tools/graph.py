"""그래프 분석 도구."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from obsidian_mcp.vault import ObsidianVault


def register(mcp: FastMCP, vault: ObsidianVault) -> None:
    """그래프 분석 도구를 MCP 서버에 등록한다."""

    @mcp.tool()
    async def get_backlinks(note_path: str) -> list[str]:
        """특정 노트를 참조하는 다른 노트 목록을 조회합니다.

        Args:
            note_path: 대상 노트 경로
        """
        return vault.get_backlinks(note_path)

    @mcp.tool()
    async def get_forward_links(note_path: str) -> list[str]:
        """특정 노트가 참조하는 다른 노트 목록을 조회합니다.

        Args:
            note_path: 대상 노트 경로
        """
        return vault.get_forward_links(note_path)

    @mcp.tool()
    async def get_graph() -> dict:
        """전체 노트 연결 그래프를 조회합니다. 노드(노트)와 엣지(링크) 정보를 반환합니다."""
        return vault.get_graph()
