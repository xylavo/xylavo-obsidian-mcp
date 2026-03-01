"""Obsidian Vault 파일시스템 접근 계층.

모든 도구(tools)는 이 모듈을 통해서만 Vault 파일에 접근한다.
"""

from __future__ import annotations

import fnmatch
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
from obsidian_mcp.utils.markdown import (
    extract_all_links,
    extract_inline_tags,
    parse_sections,
    reconstruct_body,
)

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

    # ── 설정 파일 (.obsidian-mcp.json) ─────────────────────

    def _config_path(self) -> Path:
        return self.root / ".obsidian-mcp.json"

    def _load_config(self) -> dict:
        """설정 파일을 읽는다. 없으면 빈 dict를 반환한다."""
        cp = self._config_path()
        if not cp.is_file():
            return {}
        return json.loads(cp.read_text(encoding="utf-8"))

    def _save_config(self, config: dict) -> None:
        """설정 파일을 저장한다."""
        cp = self._config_path()
        cp.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")

    def _match_folder_pattern(self, folder: str, pattern: str) -> bool:
        """폴더 경로가 와일드카드 패턴에 매칭되는지 확인한다.

        * : 단일 경로 세그먼트 매칭 (예: 프로젝트/*/회의록)
        ** : 0개 이상의 경로 세그먼트 매칭 (예: 프로젝트/**/회의록)
        """
        return self._match_parts(folder.split("/"), pattern.split("/"))

    def _match_parts(
        self, folder_parts: list[str], pattern_parts: list[str],
    ) -> bool:
        """경로 세그먼트를 재귀적으로 매칭한다."""
        if not pattern_parts:
            return not folder_parts
        if pattern_parts[0] == "**":
            rest = pattern_parts[1:]
            for i in range(len(folder_parts) + 1):
                if self._match_parts(folder_parts[i:], rest):
                    return True
            return False
        if not folder_parts:
            return False
        if fnmatch.fnmatch(folder_parts[0], pattern_parts[0]):
            return self._match_parts(folder_parts[1:], pattern_parts[1:])
        return False

    def _pattern_specificity(self, pattern: str) -> tuple[int, int]:
        """패턴의 구체성을 반환한다. (총 세그먼트 수, 리터럴 세그먼트 수)"""
        parts = pattern.split("/")
        total = len(parts)
        literal = sum(1 for p in parts if "*" not in p and "?" not in p)
        return (total, literal)

    def get_folder_template(self, folder: str) -> str | None:
        """폴더에 매핑된 템플릿을 반환한다.

        우선순위: 정확한 매칭 → 와일드카드 패턴 (구체적인 순) → 상위 폴더.
        """
        config = self._load_config()
        mapping = config.get("folder_templates", {})
        # 폴더 경로 정규화 (백슬래시 → 슬래시, 끝 슬래시 제거)
        folder = folder.replace("\\", "/").strip("/")

        # 1. 정확한 매칭
        if folder in mapping:
            return mapping[folder]

        # 2. 와일드카드 패턴 매칭 (가장 구체적인 패턴 우선)
        wildcard_matches: list[tuple[tuple[int, int], str]] = []
        for pattern, template in mapping.items():
            if "*" in pattern or "?" in pattern:
                if self._match_folder_pattern(folder, pattern):
                    specificity = self._pattern_specificity(pattern)
                    wildcard_matches.append((specificity, template))
        if wildcard_matches:
            wildcard_matches.sort(reverse=True)
            return wildcard_matches[0][1]

        # 3. 상위 폴더 순으로 탐색
        parts = folder.split("/")
        for i in range(len(parts) - 1, 0, -1):
            parent = "/".join(parts[:i])
            if parent in mapping:
                return mapping[parent]
        return None

    def set_folder_template(self, folder: str, template_name: str) -> dict:
        """폴더-템플릿 매핑을 설정한다."""
        # 템플릿 존재 확인
        tpl_root = self._template_root()
        tpl_name = template_name if template_name.endswith(".md") else template_name + ".md"
        tpl_file = (tpl_root / tpl_name).resolve()
        if not tpl_file.is_file():
            raise VaultError(f"템플릿을 찾을 수 없습니다: {template_name}")
        folder = folder.replace("\\", "/").strip("/")
        config = self._load_config()
        if "folder_templates" not in config:
            config["folder_templates"] = {}
        config["folder_templates"][folder] = template_name
        self._save_config(config)
        return {"folder": folder, "template": template_name, "set": True}

    def remove_folder_template(self, folder: str) -> dict:
        """폴더-템플릿 매핑을 제거한다."""
        folder = folder.replace("\\", "/").strip("/")
        config = self._load_config()
        mapping = config.get("folder_templates", {})
        if folder not in mapping:
            raise VaultError(f"폴더 매핑이 존재하지 않습니다: {folder}")
        removed_template = mapping.pop(folder)
        config["folder_templates"] = mapping
        self._save_config(config)
        return {"folder": folder, "template": removed_template, "removed": True}

    def list_folder_templates(self) -> dict[str, str]:
        """전체 폴더-템플릿 매핑을 반환한다."""
        config = self._load_config()
        return config.get("folder_templates", {})

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
        template_name: str | None = None,
        variables: dict | None = None,
    ) -> dict:
        """새 노트를 생성한다.

        우선순위: template_name 직접 지정 > 폴더 매핑 템플릿 > content/metadata 사용.
        content가 비어 있고 template_name도 없으면 폴더 매핑을 확인한다.
        """
        fp = self._resolve(note_path)
        if fp.exists():
            raise VaultError(f"노트가 이미 존재합니다: {note_path}")

        # 템플릿 결정: 직접 지정 > 폴더 매핑 (content가 비어 있을 때만)
        effective_template = template_name
        if effective_template is None and not content and metadata is None:
            folder = fp.relative_to(self.root).parent.as_posix()
            if folder and folder != ".":
                effective_template = self.get_folder_template(folder)

        # 템플릿 적용
        if effective_template:
            tpl_root = self._template_root()
            tpl_name = effective_template if effective_template.endswith(".md") else effective_template + ".md"
            tpl_file = (tpl_root / tpl_name).resolve()
            if not tpl_file.is_file():
                raise VaultError(f"템플릿을 찾을 수 없습니다: {effective_template}")
            tpl_content = tpl_file.read_text(encoding="utf-8")
            if variables:
                for key, value in variables.items():
                    tpl_content = tpl_content.replace("{{" + key + "}}", str(value))
            tpl_meta, tpl_body = parse_note(tpl_content)
            content = tpl_body
            metadata = tpl_meta

        fp.parent.mkdir(parents=True, exist_ok=True)
        text = serialize_note(metadata or {}, content)
        fp.write_text(text, encoding="utf-8")
        result = {"path": self._relative(fp), "created": True}
        if effective_template:
            result["template_applied"] = effective_template
        return result

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

    # ── 섹션 ──────────────────────────────────────────────

    def _match_heading(self, sections: list[dict], heading: str) -> dict | None:
        """헤딩 문자열로 섹션을 찾는다. # prefix 유무 모두 허용."""
        heading_stripped = heading.lstrip("# ").strip()
        for sec in sections:
            if sec["heading"] is None:
                continue
            sec_stripped = sec["heading"].lstrip("# ").strip()
            if sec_stripped == heading_stripped:
                return sec
        return None

    def list_note_sections(self, note_path: str) -> list[dict]:
        """노트의 섹션 목록(index, heading, level)을 반환한다."""
        data = self.read_note(note_path)
        sections = parse_sections(data["content"])
        return [
            {"index": s["index"], "heading": s["heading"], "level": s["level"]}
            for s in sections
        ]

    def read_note_section(self, note_path: str, heading: str) -> dict:
        """특정 헤딩의 섹션 내용을 반환한다."""
        data = self.read_note(note_path)
        sections = parse_sections(data["content"])
        sec = self._match_heading(sections, heading)
        if sec is None:
            raise VaultError(f"섹션을 찾을 수 없습니다: {heading}")
        return {"heading": sec["heading"], "content": sec["content"]}

    def update_note_section(self, note_path: str, heading: str, content: str) -> dict:
        """특정 헤딩의 섹션 내용만 교체한다. 헤딩 자체는 유지."""
        fp = self._resolve(note_path)
        if not fp.is_file():
            raise VaultError(f"노트를 찾을 수 없습니다: {note_path}")
        raw = fp.read_text(encoding="utf-8")
        meta, body = parse_note(raw)
        sections = parse_sections(body)
        sec = self._match_heading(sections, heading)
        if sec is None:
            raise VaultError(f"섹션을 찾을 수 없습니다: {heading}")
        sections[sec["index"]]["content"] = content
        new_body = reconstruct_body(sections)
        fp.write_text(serialize_note(meta, new_body), encoding="utf-8")
        return {"path": self._relative(fp), "section_updated": True}

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
        return self.create_note(
            note_path, template_name=template_name, variables=variables,
        )

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
