"""Obsidian Vault 파일시스템 접근 계층.

모든 도구(tools)는 이 모듈을 통해서만 Vault 파일에 접근한다.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from obsidian_mcp.utils.frontmatter import (
    get_tags_from_metadata,
    parse_note,
    serialize_note,
    set_tags_in_metadata,
)
from obsidian_mcp.utils.markdown import extract_all_links, extract_inline_tags

logger = logging.getLogger(__name__)


class VaultError(Exception):
    """Vault 작업 관련 예외."""


class ObsidianVault:
    """Obsidian Vault 파일시스템 접근 클래스."""

    def __init__(
        self,
        vault_path: str | None = None,
        template_dir: str = "Templates",
        exclude_patterns: list[str] | None = None,
    ):
        vault_path = vault_path or os.environ.get("OBSIDIAN_VAULT_PATH")
        if not vault_path:
            raise VaultError(
                "OBSIDIAN_VAULT_PATH 환경 변수가 설정되지 않았습니다."
            )

        self.root = Path(vault_path).resolve()
        if not self.root.is_dir():
            raise VaultError(f"Vault 경로가 존재하지 않습니다: {self.root}")

        self.template_dir = template_dir
        self.exclude_patterns = exclude_patterns or [".obsidian", ".trash"]

    # ── 경로 유틸 ──────────────────────────────────────────

    def _resolve(self, note_path: str) -> Path:
        """상대 경로를 Vault 내 절대 경로로 변환하고 검증한다."""
        if not note_path.endswith(".md"):
            note_path += ".md"
        full = (self.root / note_path).resolve()
        if not str(full).startswith(str(self.root)):
            raise VaultError("Vault 밖 경로에 접근할 수 없습니다.")
        return full

    def _relative(self, full_path: Path) -> str:
        """절대 경로를 Vault 기준 상대 경로(POSIX)로 변환한다."""
        return full_path.relative_to(self.root).as_posix()

    def _is_excluded(self, path: Path) -> bool:
        """제외 패턴에 해당하는지 확인한다."""
        rel = self._relative(path)
        return any(rel.startswith(pat) for pat in self.exclude_patterns)

    # ── 노트 목록 ─────────────────────────────────────────

    def list_notes(self) -> list[str]:
        """Vault 내 모든 .md 파일의 상대 경로 목록을 반환한다."""
        notes: list[str] = []
        for p in self.root.rglob("*.md"):
            if not self._is_excluded(p):
                notes.append(self._relative(p))
        notes.sort()
        return notes

    # ── 노트 CRUD ─────────────────────────────────────────

    def read_note(self, note_path: str) -> dict:
        """노트를 읽어 메타데이터와 본문을 반환한다."""
        fp = self._resolve(note_path)
        if not fp.is_file():
            raise VaultError(f"노트를 찾을 수 없습니다: {note_path}")
        content = fp.read_text(encoding="utf-8")
        metadata, body = parse_note(content)
        return {
            "path": self._relative(fp),
            "metadata": metadata,
            "content": body,
        }

    def create_note(
        self,
        note_path: str,
        content: str = "",
        metadata: dict | None = None,
    ) -> dict:
        """새 노트를 생성한다."""
        fp = self._resolve(note_path)
        if fp.exists():
            raise VaultError(f"노트가 이미 존재합니다: {note_path}")
        fp.parent.mkdir(parents=True, exist_ok=True)
        text = serialize_note(metadata or {}, content)
        fp.write_text(text, encoding="utf-8")
        return {"path": self._relative(fp), "created": True}

    def update_note(
        self,
        note_path: str,
        content: str | None = None,
        metadata: dict | None = None,
    ) -> dict:
        """기존 노트의 본문 또는 메타데이터를 수정한다."""
        fp = self._resolve(note_path)
        if not fp.is_file():
            raise VaultError(f"노트를 찾을 수 없습니다: {note_path}")
        raw = fp.read_text(encoding="utf-8")
        old_meta, old_body = parse_note(raw)
        new_meta = {**old_meta, **(metadata or {})}
        new_body = content if content is not None else old_body
        fp.write_text(serialize_note(new_meta, new_body), encoding="utf-8")
        return {"path": self._relative(fp), "updated": True}

    def append_to_note(self, note_path: str, content: str) -> dict:
        """노트 끝에 내용을 추가한다."""
        fp = self._resolve(note_path)
        if not fp.is_file():
            raise VaultError(f"노트를 찾을 수 없습니다: {note_path}")
        raw = fp.read_text(encoding="utf-8")
        meta, body = parse_note(raw)
        new_body = body.rstrip() + "\n\n" + content
        fp.write_text(serialize_note(meta, new_body), encoding="utf-8")
        return {"path": self._relative(fp), "appended": True}

    def delete_note(self, note_path: str) -> dict:
        """노트를 삭제한다."""
        fp = self._resolve(note_path)
        if not fp.is_file():
            raise VaultError(f"노트를 찾을 수 없습니다: {note_path}")
        rel = self._relative(fp)
        fp.unlink()
        return {"path": rel, "deleted": True}

    # ── 검색 ──────────────────────────────────────────────

    def search_notes(self, query: str) -> list[dict]:
        """전문 검색 — 본문과 제목에서 쿼리를 찾는다."""
        query_lower = query.lower()
        results: list[dict] = []
        for note_path in self.list_notes():
            fp = self._resolve(note_path)
            content = fp.read_text(encoding="utf-8")
            if query_lower in content.lower() or query_lower in note_path.lower():
                _, body = parse_note(content)
                # 매칭 라인 미리보기
                lines = body.splitlines()
                matches = [
                    ln for ln in lines if query_lower in ln.lower()
                ]
                results.append(
                    {
                        "path": note_path,
                        "matches": matches[:5],
                    }
                )
        return results

    def search_by_tag(self, tag: str) -> list[str]:
        """특정 태그를 가진 노트 목록을 반환한다."""
        tag = tag.lstrip("#")
        results: list[str] = []
        for note_path in self.list_notes():
            fp = self._resolve(note_path)
            content = fp.read_text(encoding="utf-8")
            meta, body = parse_note(content)
            all_tags = get_tags_from_metadata(meta) + extract_inline_tags(body)
            if tag in all_tags:
                results.append(note_path)
        return results

    # ── 태그 ──────────────────────────────────────────────

    def list_tags(self) -> dict[str, int]:
        """Vault 전체의 태그와 사용 빈도를 반환한다."""
        tag_count: dict[str, int] = {}
        for note_path in self.list_notes():
            fp = self._resolve(note_path)
            content = fp.read_text(encoding="utf-8")
            meta, body = parse_note(content)
            tags = get_tags_from_metadata(meta) + extract_inline_tags(body)
            for t in tags:
                tag_count[t] = tag_count.get(t, 0) + 1
        return dict(sorted(tag_count.items(), key=lambda x: -x[1]))

    def add_tag(self, note_path: str, tag: str) -> dict:
        """노트 프론트매터에 태그를 추가한다."""
        tag = tag.lstrip("#")
        fp = self._resolve(note_path)
        if not fp.is_file():
            raise VaultError(f"노트를 찾을 수 없습니다: {note_path}")
        content = fp.read_text(encoding="utf-8")
        meta, body = parse_note(content)
        tags = get_tags_from_metadata(meta)
        if tag in tags:
            return {"path": self._relative(fp), "tag": tag, "added": False, "reason": "이미 존재"}
        tags.append(tag)
        meta = set_tags_in_metadata(meta, tags)
        fp.write_text(serialize_note(meta, body), encoding="utf-8")
        return {"path": self._relative(fp), "tag": tag, "added": True}

    def remove_tag(self, note_path: str, tag: str) -> dict:
        """노트 프론트매터에서 태그를 제거한다."""
        tag = tag.lstrip("#")
        fp = self._resolve(note_path)
        if not fp.is_file():
            raise VaultError(f"노트를 찾을 수 없습니다: {note_path}")
        content = fp.read_text(encoding="utf-8")
        meta, body = parse_note(content)
        tags = get_tags_from_metadata(meta)
        if tag not in tags:
            return {"path": self._relative(fp), "tag": tag, "removed": False, "reason": "태그 없음"}
        tags.remove(tag)
        meta = set_tags_in_metadata(meta, tags)
        fp.write_text(serialize_note(meta, body), encoding="utf-8")
        return {"path": self._relative(fp), "tag": tag, "removed": True}

    # ── 그래프 ────────────────────────────────────────────

    def _build_link_map(self) -> dict[str, list[str]]:
        """모든 노트의 링크를 파싱하여 {노트: [링크대상]} 맵을 만든다."""
        link_map: dict[str, list[str]] = {}
        for note_path in self.list_notes():
            fp = self._resolve(note_path)
            content = fp.read_text(encoding="utf-8")
            _, body = parse_note(content)
            links = extract_all_links(body)
            link_map[note_path] = links
        return link_map

    def _normalize_link_target(self, target: str) -> str | None:
        """링크 대상을 Vault 내 상대 경로로 정규화한다. 못 찾으면 None."""
        if not target.endswith(".md"):
            target_md = target + ".md"
        else:
            target_md = target

        # 정확한 경로 매칭
        fp = (self.root / target_md).resolve()
        if fp.is_file() and str(fp).startswith(str(self.root)):
            return self._relative(fp)

        # 파일명으로 검색 (Obsidian의 shortest-path 방식)
        name = Path(target_md).name
        for p in self.root.rglob(name):
            if not self._is_excluded(p) and p.is_file():
                return self._relative(p)
        return None

    def get_backlinks(self, note_path: str) -> list[str]:
        """특정 노트를 참조하는 다른 노트들을 반환한다."""
        fp = self._resolve(note_path)
        if not fp.is_file():
            raise VaultError(f"노트를 찾을 수 없습니다: {note_path}")
        target_rel = self._relative(fp)
        target_stem = fp.stem

        backlinks: list[str] = []
        link_map = self._build_link_map()
        for src, links in link_map.items():
            if src == target_rel:
                continue
            for lnk in links:
                normalized = self._normalize_link_target(lnk)
                if normalized == target_rel:
                    backlinks.append(src)
                    break
                # 이름만으로도 매칭 (Obsidian 방식)
                if Path(lnk).stem == target_stem:
                    backlinks.append(src)
                    break
        return sorted(set(backlinks))

    def get_forward_links(self, note_path: str) -> list[str]:
        """특정 노트가 참조하는 다른 노트들을 반환한다."""
        fp = self._resolve(note_path)
        if not fp.is_file():
            raise VaultError(f"노트를 찾을 수 없습니다: {note_path}")
        content = fp.read_text(encoding="utf-8")
        _, body = parse_note(content)
        raw_links = extract_all_links(body)

        forward: list[str] = []
        for lnk in raw_links:
            normalized = self._normalize_link_target(lnk)
            if normalized:
                forward.append(normalized)
        return sorted(set(forward))

    def get_graph(self) -> dict:
        """전체 노트 연결 그래프를 반환한다."""
        link_map = self._build_link_map()
        nodes = set(link_map.keys())
        edges: list[dict] = []
        for src, links in link_map.items():
            for lnk in links:
                normalized = self._normalize_link_target(lnk)
                if normalized:
                    nodes.add(normalized)
                    edges.append({"from": src, "to": normalized})
        return {
            "nodes": sorted(nodes),
            "edges": edges,
            "node_count": len(nodes),
            "edge_count": len(edges),
        }

    # ── 템플릿 ────────────────────────────────────────────

    def _template_root(self) -> Path:
        return self.root / self.template_dir

    def list_templates(self) -> list[str]:
        """사용 가능한 템플릿 목록을 반환한다."""
        tpl_root = self._template_root()
        if not tpl_root.is_dir():
            return []
        templates: list[str] = []
        for p in tpl_root.rglob("*.md"):
            templates.append(p.relative_to(tpl_root).as_posix())
        templates.sort()
        return templates

    def create_from_template(
        self,
        template_name: str,
        note_path: str,
        variables: dict | None = None,
    ) -> dict:
        """템플릿을 기반으로 새 노트를 생성한다."""
        tpl_root = self._template_root()
        if not template_name.endswith(".md"):
            template_name += ".md"
        tpl_file = (tpl_root / template_name).resolve()
        if not tpl_file.is_file():
            raise VaultError(f"템플릿을 찾을 수 없습니다: {template_name}")

        tpl_content = tpl_file.read_text(encoding="utf-8")

        # 간단한 변수 치환: {{variable_name}}
        if variables:
            for key, value in variables.items():
                tpl_content = tpl_content.replace("{{" + key + "}}", str(value))

        meta, body = parse_note(tpl_content)
        return self.create_note(note_path, content=body, metadata=meta)

    # ── Vault 정보 ────────────────────────────────────────

    def get_vault_structure(self) -> dict:
        """Vault 폴더 구조를 반환한다."""

        def _build_tree(directory: Path) -> dict:
            tree: dict = {"name": directory.name, "type": "folder", "children": []}
            try:
                entries = sorted(directory.iterdir(), key=lambda p: (p.is_file(), p.name))
            except PermissionError:
                return tree
            for entry in entries:
                if self._is_excluded(entry):
                    continue
                if entry.is_dir():
                    tree["children"].append(_build_tree(entry))
                elif entry.suffix == ".md":
                    tree["children"].append(
                        {"name": entry.name, "type": "file", "path": self._relative(entry)}
                    )
            return tree

        return _build_tree(self.root)

    def get_vault_stats(self) -> dict:
        """Vault 통계를 반환한다."""
        notes = self.list_notes()
        tags = self.list_tags()
        link_map = self._build_link_map()
        total_links = sum(len(v) for v in link_map.values())
        return {
            "total_notes": len(notes),
            "total_tags": len(tags),
            "total_links": total_links,
            "vault_path": str(self.root),
        }
