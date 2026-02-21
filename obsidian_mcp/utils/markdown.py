"""마크다운 파싱 유틸리티 — 링크, 인라인 태그 추출."""

from __future__ import annotations

import re

# [[wikilink]] 또는 [[wikilink|alias]]
_WIKILINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]")

# [text](link.md) — 외부 URL(http)은 제외
_MDLINK_RE = re.compile(r"\[(?:[^\]]*)\]\((?!https?://)([^)]+)\)")

# 인라인 태그: #tag (프론트매터 밖 본문에서)
_INLINE_TAG_RE = re.compile(r"(?:^|(?<=\s))#([A-Za-z0-9가-힣_/\-]+)")

# 코드블록(``` ```) 및 인라인 코드(` `) 제거용
_CODEBLOCK_RE = re.compile(r"```[\s\S]*?```|`[^`]+`")


def extract_wikilinks(text: str) -> list[str]:
    """본문에서 [[wikilink]] 대상을 추출한다."""
    return _WIKILINK_RE.findall(text)


def extract_markdown_links(text: str) -> list[str]:
    """본문에서 [text](relative-link) 대상을 추출한다."""
    return _MDLINK_RE.findall(text)


def extract_all_links(text: str) -> list[str]:
    """위키링크 + 마크다운 링크를 모두 추출한다."""
    links = extract_wikilinks(text)
    links.extend(extract_markdown_links(text))
    return links


def extract_inline_tags(text: str) -> list[str]:
    """본문에서 인라인 #태그를 추출한다. 코드블록 내부는 무시."""
    cleaned = _CODEBLOCK_RE.sub("", text)
    return _INLINE_TAG_RE.findall(cleaned)


# ── 섹션 파싱 ─────────────────────────────────────────────

# ATX 헤딩: ^#{1,6} 뒤에 공백과 텍스트
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$")

# Thematic break: 줄 전체가 3개 이상의 대시
_THEMATIC_BREAK_RE = re.compile(r"^-{3,}\s*$")

# 펜스드 코드블록 열림/닫힘
_FENCE_RE = re.compile(r"^(`{3,}|~{3,})")


def parse_sections(body: str) -> list[dict]:
    """마크다운 본문을 헤딩/구분선 기준으로 섹션 분할한다.

    코드블록(``` 또는 ~~~) 내부의 헤딩·구분선은 무시한다.

    Returns:
        [{"index": 0, "heading": None|str, "level": int, "content": str}, ...]
    """
    lines = body.split("\n")
    # (line_index, heading_text, level) — 분할 지점 수집
    splits: list[tuple[int, str | None, int]] = []
    in_fence = False
    fence_marker = ""

    for i, line in enumerate(lines):
        # 코드블록 토글
        fence_match = _FENCE_RE.match(line.strip())
        if fence_match:
            marker = fence_match.group(1)[0]  # ` 또는 ~
            if not in_fence:
                in_fence = True
                fence_marker = marker
            elif line.strip().startswith(fence_marker[0] * 3) and marker == fence_marker:
                in_fence = False
                fence_marker = ""
            continue

        if in_fence:
            continue

        # ATX 헤딩
        heading_match = _HEADING_RE.match(line)
        if heading_match:
            level = len(heading_match.group(1))
            splits.append((i, line, level))
            continue

        # Thematic break
        if _THEMATIC_BREAK_RE.match(line):
            splits.append((i, "---", 0))

    # 분할 지점이 없으면 전체를 하나의 섹션으로
    if not splits:
        return [{"index": 0, "heading": None, "level": 0, "content": body}]

    sections: list[dict] = []
    idx = 0

    # 첫 번째 분할 지점 이전 내용
    if splits[0][0] > 0:
        pre = "\n".join(lines[: splits[0][0]])
        sections.append({"index": idx, "heading": None, "level": 0, "content": pre})
        idx += 1

    for si, (line_no, heading, level) in enumerate(splits):
        # 다음 분할 지점까지의 내용
        next_line = splits[si + 1][0] if si + 1 < len(splits) else len(lines)
        content_lines = lines[line_no + 1 : next_line]
        content = "\n".join(content_lines)
        sections.append({
            "index": idx,
            "heading": heading,
            "level": level,
            "content": content,
        })
        idx += 1

    return sections


def reconstruct_body(sections: list[dict]) -> str:
    """섹션 리스트를 다시 마크다운 본문으로 합친다."""
    parts: list[str] = []
    for sec in sections:
        if sec["heading"] is not None:
            parts.append(sec["heading"])
        if sec["content"]:
            parts.append(sec["content"])
        elif sec["heading"] is not None:
            # 헤딩만 있고 내용이 없는 경우 빈 문자열 추가하지 않음
            pass
    return "\n".join(parts)
