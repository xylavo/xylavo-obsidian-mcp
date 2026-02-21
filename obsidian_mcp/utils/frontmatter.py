"""프론트매터 파싱 및 직렬화 유틸리티."""

from __future__ import annotations

import frontmatter


def parse_note(content: str) -> tuple[dict, str]:
    """노트 내용에서 프론트매터와 본문을 분리한다.

    Returns:
        (metadata dict, body string) 튜플
    """
    post = frontmatter.loads(content)
    return dict(post.metadata), post.content


def serialize_note(metadata: dict, body: str) -> str:
    """프론트매터와 본문을 합쳐 마크다운 문자열로 만든다."""
    post = frontmatter.Post(body, **metadata)
    return frontmatter.dumps(post)


def get_tags_from_metadata(metadata: dict) -> list[str]:
    """프론트매터에서 tags 필드를 추출한다."""
    tags = metadata.get("tags", [])
    if isinstance(tags, str):
        return [t.strip() for t in tags.split(",") if t.strip()]
    if isinstance(tags, list):
        return [str(t) for t in tags]
    return []


def set_tags_in_metadata(metadata: dict, tags: list[str]) -> dict:
    """프론트매터에 tags 필드를 설정한다."""
    metadata = dict(metadata)
    metadata["tags"] = tags
    return metadata
