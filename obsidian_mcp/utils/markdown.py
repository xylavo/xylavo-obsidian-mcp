"""마크다운 파싱 유틸리티 — 링크, 인라인 태그 추출."""

from __future__ import annotations

import re

# [[wikilink]] 또는 [[wikilink|alias]]
_WIKILINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]")

# [text](link.md) — 외부 URL(http)은 제외
_MDLINK_RE = re.compile(r"\[(?:[^\]]*)\]\((?!https?://)([^)]+)\)")

# 인라인 태그: #tag (프론트매터 밖 본문에서)
_INLINE_TAG_RE = re.compile(r"(?:^|(?<=\s))#([A-Za-z0-9가-힣_/\-]+)")


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
    """본문에서 인라인 #태그를 추출한다."""
    return _INLINE_TAG_RE.findall(text)
