"""템플릿 도구."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from obsidian_mcp.vault import ObsidianVault


def register(mcp: FastMCP, vault: ObsidianVault) -> None:
    """템플릿 도구를 MCP 서버에 등록한다."""

    @mcp.tool()
    async def list_templates() -> list[str]:
        """사용 가능한 템플릿 목록을 조회합니다."""
        return vault.list_templates()

    @mcp.tool()
    async def create_from_template(
        template_name: str,
        note_path: str,
        variables: dict | None = None,
    ) -> dict:
        """템플릿을 기반으로 새 노트를 생성합니다.

        Args:
            template_name: 템플릿 이름 (예: "daily.md")
            note_path: 생성할 노트 경로
            variables: 템플릿 변수 (예: {"title": "회의록", "date": "2025-01-01"})
        """
        return vault.create_from_template(template_name, note_path, variables=variables)
