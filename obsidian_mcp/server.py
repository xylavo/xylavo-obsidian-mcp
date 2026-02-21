"""MCP 서버 정의 — 도구 및 리소스 등록."""

from __future__ import annotations

import json
import logging
import os

from mcp.server.fastmcp import FastMCP

from obsidian_mcp.vault import ObsidianVault
from obsidian_mcp.tools import graph, notes, search, tags, templates

logger = logging.getLogger(__name__)

# ── FastMCP 서버 인스턴스 ─────────────────────────────────

mcp = FastMCP("obsidian")

# ── Vault 인스턴스 (lazy init) ────────────────────────────

_vault: ObsidianVault | None = None


def _get_vault() -> ObsidianVault:
    global _vault
    if _vault is None:
        _vault = ObsidianVault(
            vault_path=os.environ.get("OBSIDIAN_VAULT_PATH"),
            template_dir=os.environ.get("OBSIDIAN_TEMPLATE_DIR", "Templates"),
            exclude_patterns=os.environ.get(
                "OBSIDIAN_EXCLUDE_PATTERNS", ".obsidian,.trash"
            ).split(","),
        )
    return _vault


# ── 도구 등록 ─────────────────────────────────────────────

def _register_all() -> None:
    vault = _get_vault()
    notes.register(mcp, vault)
    search.register(mcp, vault)
    tags.register(mcp, vault)
    graph.register(mcp, vault)
    templates.register(mcp, vault)


_register_all()


# ── 리소스 등록 ───────────────────────────────────────────

@mcp.resource("obsidian://notes")
def resource_list_notes() -> str:
    """Vault 내 전체 노트 목록을 반환합니다."""
    vault = _get_vault()
    return json.dumps(vault.list_notes(), ensure_ascii=False)


@mcp.resource("obsidian://note/{path}")
def resource_read_note(path: str) -> str:
    """특정 노트의 내용을 반환합니다."""
    vault = _get_vault()
    return json.dumps(vault.read_note(path), ensure_ascii=False)


@mcp.resource("obsidian://tags")
def resource_list_tags() -> str:
    """전체 태그 목록을 반환합니다."""
    vault = _get_vault()
    return json.dumps(vault.list_tags(), ensure_ascii=False)


@mcp.resource("obsidian://structure")
def resource_vault_structure() -> str:
    """Vault 폴더 구조를 반환합니다."""
    vault = _get_vault()
    return json.dumps(vault.get_vault_structure(), ensure_ascii=False)
