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

    # ── 폴더-템플릿 매핑 ──────────────────────────────────

    @mcp.tool()
    async def list_folder_templates() -> dict[str, str]:
        """폴더-템플릿 매핑 전체 목록을 조회합니다."""
        return vault.list_folder_templates()

    @mcp.tool()
    async def set_folder_template(folder: str, template_name: str) -> dict:
        """폴더에 기본 템플릿을 매핑합니다. 매핑된 폴더에서 create_note 시 템플릿이 자동 적용됩니다.

        와일드카드 패턴을 지원합니다:
        - * : 단일 경로 세그먼트 매칭 (예: "프로젝트/*/회의록")
        - ** : 0개 이상의 경로 세그먼트 매칭 (예: "프로젝트/**/회의록")

        Args:
            folder: 폴더 경로 (예: "일기", "프로젝트/*/회의록")
            template_name: 템플릿 이름 (예: "daily.md")
        """
        return vault.set_folder_template(folder, template_name)

    @mcp.tool()
    async def remove_folder_template(folder: str) -> dict:
        """폴더의 기본 템플릿 매핑을 제거합니다.

        Args:
            folder: 매핑을 제거할 폴더 경로
        """
        return vault.remove_folder_template(folder)
