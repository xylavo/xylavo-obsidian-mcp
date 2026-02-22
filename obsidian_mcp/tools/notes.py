"""노트 CRUD 도구."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from obsidian_mcp.vault import ObsidianVault


def register(mcp: FastMCP, vault: ObsidianVault) -> None:
    """노트 CRUD 도구를 MCP 서버에 등록한다."""

    @mcp.tool()
    async def read_note(note_path: str) -> dict:
        """노트의 내용과 메타데이터를 읽습니다.

        Args:
            note_path: 노트 경로 (예: "folder/note.md" 또는 "folder/note")
        """
        return vault.read_note(note_path)

    @mcp.tool()
    async def create_note(
        note_path: str,
        content: str = "",
        metadata: dict | None = None,
    ) -> dict:
        """새 노트를 생성합니다. 이 도구를 사용하기 전에 먼저 list_templates로 적절한 템플릿이 있는지 확인하고, 템플릿이 있다면 create_from_template를 대신 사용하세요.

        Args:
            note_path: 생성할 노트 경로
            content: 노트 본문 내용
            metadata: 프론트매터 메타데이터 (선택)
        """
        return vault.create_note(note_path, content=content, metadata=metadata)

    @mcp.tool()
    async def update_note(
        note_path: str,
        content: str | None = None,
        metadata: dict | None = None,
    ) -> dict:
        """기존 노트의 내용 또는 메타데이터를 수정합니다. 변경량이 적은 경우에 사용하세요. 노트 내용이 길거나 변경할 양이 많으면 update_note_section을 사용하여 특정 섹션만 수정하는 것이 효율적입니다.

        Args:
            note_path: 수정할 노트 경로
            content: 새 본문 내용 (None이면 기존 유지)
            metadata: 병합할 메타데이터 (None이면 기존 유지)
        """
        return vault.update_note(note_path, content=content, metadata=metadata)

    @mcp.tool()
    async def append_to_note(note_path: str, content: str) -> dict:
        """노트 끝에 내용을 추가합니다.

        Args:
            note_path: 대상 노트 경로
            content: 추가할 내용
        """
        return vault.append_to_note(note_path, content)

    @mcp.tool()
    async def delete_note(note_path: str) -> dict:
        """노트를 삭제합니다.

        Args:
            note_path: 삭제할 노트 경로
        """
        return vault.delete_note(note_path)

    # ── 섹션 기반 편집 ────────────────────────────────────

    @mcp.tool()
    async def list_note_sections(note_path: str) -> list[dict]:
        """노트의 섹션(헤딩) 목록을 조회합니다.

        Args:
            note_path: 노트 경로 (예: "folder/note.md" 또는 "folder/note")
        """
        return vault.list_note_sections(note_path)

    @mcp.tool()
    async def read_note_section(note_path: str, heading: str) -> dict:
        """특정 섹션의 내용만 읽습니다.

        Args:
            note_path: 노트 경로
            heading: 섹션 헤딩 (예: "# 매일 할 일" 또는 "매일 할 일")
        """
        return vault.read_note_section(note_path, heading)

    @mcp.tool()
    async def update_note_section(note_path: str, heading: str, content: str) -> dict:
        """특정 섹션의 내용만 수정합니다. 헤딩은 유지됩니다. 노트 내용이 길거나 변경할 양이 많을 때는 update_note 대신 이 도구를 사용하여 해당 섹션만 수정하세요.

        Args:
            note_path: 노트 경로
            heading: 섹션 헤딩 (예: "# 매일 할 일" 또는 "매일 할 일")
            content: 새 섹션 내용 (헤딩 제외)
        """
        return vault.update_note_section(note_path, heading, content)
