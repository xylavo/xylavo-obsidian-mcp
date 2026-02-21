"""태그 관리 도구."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from obsidian_mcp.vault import ObsidianVault


def register(mcp: FastMCP, vault: ObsidianVault) -> None:
    """태그 관리 도구를 MCP 서버에 등록한다."""

    @mcp.tool()
    async def list_tags() -> dict[str, int]:
        """Vault 전체의 태그 목록과 사용 빈도를 조회합니다."""
        return vault.list_tags()

    @mcp.tool()
    async def add_tag(note_path: str, tag: str) -> dict:
        """노트에 태그를 추가합니다.

        Args:
            note_path: 대상 노트 경로
            tag: 추가할 태그 (예: "project")
        """
        return vault.add_tag(note_path, tag)

    @mcp.tool()
    async def remove_tag(note_path: str, tag: str) -> dict:
        """노트에서 태그를 제거합니다.

        Args:
            note_path: 대상 노트 경로
            tag: 제거할 태그
        """
        return vault.remove_tag(note_path, tag)
