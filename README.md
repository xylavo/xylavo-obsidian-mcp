# Obsidian MCP Server

Obsidian Vault를 AI 어시스턴트에서 직접 활용할 수 있게 해주는 [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) 서버입니다.
로컬 파일시스템을 통해 Vault에 접근하며, 노트 CRUD, 검색, 그래프 분석, 백링크 조회 등 다양한 기능을 제공합니다.

## 주요 기능

### 노트 관리 (CRUD)
- **노트 읽기** — 마크다운 노트 내용 및 프론트매터 조회
- **노트 생성** — 새 노트 생성 (템플릿 적용 가능)
- **노트 수정** — 기존 노트 내용 수정, 내용 추가(append/prepend)
- **노트 삭제** — 노트 삭제

### 검색
- **전문 검색** — Vault 내 노트 전문(full-text) 검색
- **태그 검색** — 특정 태그가 달린 노트 목록 조회
- **프론트매터 검색** — 메타데이터 기반 필터링

### 태그 관리
- **태그 목록 조회** — Vault 전체 태그 목록 및 사용 빈도
- **태그 추가/제거** — 노트에 태그 추가 또는 제거

### 그래프 분석
- **백링크 조회** — 특정 노트를 참조하는 다른 노트 목록
- **포워드 링크 조회** — 특정 노트가 참조하는 다른 노트 목록
- **연결 그래프** — 노트 간 연결 관계 분석

### 템플릿
- **템플릿 목록 조회** — 사용 가능한 템플릿 목록
- **템플릿 적용** — 노트 생성 시 템플릿 기반으로 생성

### Vault 정보
- **Vault 구조 조회** — 폴더 구조 및 파일 목록
- **Vault 통계** — 총 노트 수, 태그 수, 링크 수 등 통계

## 설치

### 요구 사항
- Python 3.11 이상
- Obsidian Vault (로컬)

### 설치

```bash
git clone https://github.com/xylavo/xylavo-obsidian-mcp.git
cd xylavo-obsidian-mcp
pip install -e .
```

## 설정

### MCP 클라이언트 설정

Claude Desktop (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "obsidian": {
      "command": "python",
      "args": ["-m", "obsidian_mcp"],
      "env": {
        "OBSIDIAN_VAULT_PATH": "/path/to/your/vault"
      }
    }
  }
}
```

### 환경 변수

| 변수 | 설명 | 기본값 |
|---|---|---|
| `OBSIDIAN_VAULT_PATH` | Obsidian Vault 경로 (필수) | — |
| `OBSIDIAN_TEMPLATE_DIR` | 템플릿 폴더 경로 (Vault 기준 상대경로) | `Templates` |
| `OBSIDIAN_EXCLUDE_PATTERNS` | 제외할 파일/폴더 패턴 (쉼표 구분) | `.obsidian,.trash` |

## 제공 도구 (Tools)

| 도구 | 설명 |
|---|---|
| `read_note` | 노트 내용 및 메타데이터 읽기 |
| `create_note` | 새 노트 생성 |
| `update_note` | 노트 내용 수정 |
| `append_to_note` | 노트 끝에 내용 추가 |
| `delete_note` | 노트 삭제 |
| `search_notes` | 전문 검색 |
| `search_by_tag` | 태그 기반 검색 |
| `list_tags` | 태그 목록 조회 |
| `add_tag` | 노트에 태그 추가 |
| `remove_tag` | 노트에서 태그 제거 |
| `get_backlinks` | 백링크 조회 |
| `get_forward_links` | 포워드 링크 조회 |
| `get_graph` | 연결 그래프 조회 |
| `list_templates` | 템플릿 목록 |
| `create_from_template` | 템플릿으로 노트 생성 |
| `get_vault_structure` | Vault 폴더 구조 조회 |
| `get_vault_stats` | Vault 통계 조회 |

## 제공 리소스 (Resources)

| 리소스 URI | 설명 |
|---|---|
| `obsidian://notes` | Vault 내 전체 노트 목록 |
| `obsidian://note/{path}` | 특정 노트 내용 |
| `obsidian://tags` | 전체 태그 목록 |
| `obsidian://structure` | Vault 폴더 구조 |

## 사용 예시

MCP 클라이언트(예: Claude Desktop)에서 연결 후:

```
"오늘 회의 노트를 만들어줘"
→ create_note 도구를 사용하여 노트 생성

"프로젝트 관련 노트를 검색해줘"
→ search_notes 도구로 전문 검색 실행

"이 노트를 참조하는 다른 노트가 있어?"
→ get_backlinks 도구로 백링크 조회
```

## 개발

### 개발 환경 설정

```bash
git clone https://github.com/xylavo/xylavo-obsidian-mcp.git
cd xylavo-obsidian-mcp
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

### 테스트

```bash
pytest
```

### MCP Inspector로 디버깅

```bash
npx @modelcontextprotocol/inspector python -m obsidian_mcp
```

## 프로젝트 구조

```
obsidian_mcp/
├── __init__.py
├── __main__.py          # 엔트리포인트
├── server.py            # MCP 서버 정의
├── vault.py             # Vault 파일시스템 접근 계층
├── tools/
│   ├── notes.py         # 노트 CRUD 도구
│   ├── search.py        # 검색 도구
│   ├── tags.py          # 태그 관리 도구
│   ├── graph.py         # 그래프 분석 도구
│   └── templates.py     # 템플릿 도구
└── utils/
    ├── frontmatter.py   # 프론트매터 파싱
    └── markdown.py      # 마크다운 파싱 유틸리티
```

## 라이선스

MIT License
