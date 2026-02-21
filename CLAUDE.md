# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 프로젝트 개요

Obsidian Vault를 AI 어시스턴트에서 활용할 수 있는 MCP(Model Context Protocol) 서버. 로컬 파일시스템을 통해 Vault에 직접 접근하며, 노트 CRUD, 검색, 그래프 분석, 태그 관리, 템플릿 기능을 제공한다.

## 개발 명령어

```bash
# 설치 (개발용)
pip install -e ".[dev]"

# 서버 실행
python -m obsidian_mcp

# 테스트
pytest

# MCP Inspector 디버깅
npx @modelcontextprotocol/inspector python -m obsidian_mcp
```

필수 환경 변수: `OBSIDIAN_VAULT_PATH` (Vault 절대 경로)

## 아키텍처

**계층 구조**: MCP 클라이언트 → `server.py` (FastMCP) → `tools/*.py` (도구 등록) → `vault.py` (파일시스템 접근) → `utils/` (파싱)

핵심 설계 원칙:
- **모든 파일 접근은 `ObsidianVault` 클래스(`vault.py`)를 경유**한다. 도구 모듈이 직접 파일시스템에 접근하지 않는다.
- **도구 등록 패턴**: 각 `tools/*.py` 모듈은 `register(mcp, vault)` 함수를 노출하며, `server.py`의 `_register_all()`에서 일괄 호출된다. 새 도구 모듈 추가 시 이 패턴을 따른다.
- **Vault 인스턴스는 lazy init** — `_get_vault()`가 환경 변수에서 설정을 읽어 한 번만 생성한다.
- `vault.py`의 `_resolve()`가 경로 탈출(path traversal)을 방지한다. 모든 경로 접근에 이 메서드를 사용해야 한다.

**utils 역할**:
- `frontmatter.py`: `python-frontmatter` 라이브러리 래퍼. 프론트매터 ↔ 본문 분리/합성, 태그 읽기/쓰기.
- `markdown.py`: 정규식 기반으로 `[[wikilink]]`, `[text](link.md)`, `#인라인태그` 추출.

## 주요 규칙

- 프로젝트 언어는 한국어 (docstring, 에러 메시지, README 등)
- Python 3.11+ (type union `X | Y` 문법 사용)
- 도구 함수는 `async def`로 정의하되, 실제 vault 메서드는 동기(sync)
- 노트 경로는 `.md` 확장자 생략 가능 (`_resolve()`가 자동 추가)
- 태그는 `#` prefix 없이 저장, 입력 시 `lstrip("#")`으로 정규화
