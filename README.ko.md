# llm-wiki (한국어 가이드)

Claude Code로 운영되는 개인 지식 베이스. 문서를 넣으면 Claude가 수집(ingest), 검색(query), 검사(lint), 시각화(graph)를 모두 처리합니다 — API 키나 별도 스크립트 없이도 동작합니다.

```
ingest → query → lint → graph
```

---

## 목차

- [설치](#설치)
- [프로젝트 구조](#프로젝트-구조)
- [명령어 전체 목록](#명령어-전체-목록)
- [/wiki-ingest — 문서 수집](#wiki-ingest--문서-수집)
- [/wiki-query — 지식 검색](#wiki-query--지식-검색)
- [/wiki-synthesize — 검색 결과 저장](#wiki-synthesize--검색-결과-저장)
- [/wiki-lint — 위키 건강 검사](#wiki-lint--위키-건강-검사)
- [/wiki-graph — 지식 그래프 시각화](#wiki-graph--지식-그래프-시각화)
- [/wiki-sources — 수집 이력 조회](#wiki-sources--수집-이력-조회)
- [/wiki-update — 소스 페이지 갱신](#wiki-update--소스-페이지-갱신)
- [/wiki-delete — 소스 페이지 삭제](#wiki-delete--소스-페이지-삭제)
- [/wiki-ontology — 온톨로지 관리](#wiki-ontology--온톨로지-관리)
- [페이지 형식](#페이지-형식)
- [Python 스크립트](#python-스크립트)
- [주의사항](#주의사항)

---

## 설치

### npx로 설치 (권장)

```bash
npx skills add godstale/llm-wiki
```

전역 Claude Code 스킬 디렉터리(`~/.claude/skills/llm-wiki`)에 설치됩니다.

프로젝트 단위로 설치하려면:

```bash
npx skills add godstale/llm-wiki --project
```

### 수동 설치

```bash
# 전역 설치 (모든 프로젝트에서 사용 가능)
cp -r llm-wiki ~/.claude/skills/llm-wiki

# 프로젝트 단위 설치
cp -r llm-wiki .agents/skills/llm-wiki
```

### Python 의존성 (선택)

`lint.py`, `build_graph.py` 스크립트를 사용할 때만 필요합니다. Python 없이도 에이전트 기반 폴백으로 모든 기능이 동작합니다.

```bash
pip install -r ~/.claude/skills/llm-wiki/scripts/requirements.txt
```

---

## 프로젝트 구조

스킬을 설치한 뒤 위키 프로젝트에 아래 디렉터리를 만들어두면 됩니다. 하위 디렉터리는 수집 과정에서 자동으로 생성됩니다.

```
raw/              # 드롭존 — 수집 전 원본 문서를 여기에 넣어 두세요
wiki/
  index.md        # 전체 페이지 카탈로그 (수집마다 자동 갱신)
  log.md          # 추가 전용 변경 이력
  overview.md     # 모든 소스를 아우르는 살아있는 요약
  history.json    # 수집한 소스 레지스트리
  ontology.yaml   # (선택) 프로젝트 온톨로지 스키마
  synthesis-map.md  # 저장된 검색 합성물 인덱스 (추가 전용)
  originals/      # 원본 문서 읽기 전용 보관소
  sources/        # 소스 요약 페이지 (kebab-case.md)
  entities/       # 사람, 기업, 프로젝트, 제품 (TitleCase.md)
  concepts/       # 아이디어, 프레임워크, 이론 (TitleCase.md)
  syntheses/      # 저장된 검색 답변 (kebab-case.md)
graph/            # graph.json + graph.html (자동 생성)
```

시작하려면 `raw/`와 `wiki/`만 만들면 됩니다.

---

## 명령어 전체 목록

| 명령어 | 설명 |
|--------|------|
| `/wiki-ingest [파일\|--from 폴더] [--to 폴더]` | 원본 문서를 위키에 수집 |
| `/wiki-query <질문>` | 위키를 검색하고 답변 생성 |
| `/wiki-synthesize [slug]` | 최근 검색 답변을 합성물로 저장 |
| `/wiki-lint` | 깨진 링크, 고아 페이지, 모순 등 검사 |
| `/wiki-graph` | 인터랙티브 지식 그래프 생성 |
| `/wiki-sources` | 수집 이력 목록 조회 |
| `/wiki-update <slug>` | 기존 소스 페이지 재처리 및 갱신 |
| `/wiki-delete <slug>` | 소스 페이지 및 관련 페이지 삭제 |
| `/wiki-ontology-init` | 온톨로지 스키마 초기화 |
| `/wiki-ontology-show` | 현재 온톨로지 구조 출력 |
| `/wiki-ontology-validate` | 위키 페이지와 온톨로지 정합성 검사 |

슬래시 명령어 외에 자연어로도 동작합니다:

- *"raw/my-article.md 수집해줘"*
- *"query: 주요 테마가 뭐야?"*
- *"위키 검사해줘"*
- *"지식 그래프 만들어줘"*

---

## /wiki-ingest — 문서 수집

원본 문서를 읽어 위키 페이지를 생성하고 인덱스를 갱신합니다.

### 기본 사용법

```
/wiki-ingest raw/my-article.md   # 파일 하나 수집
/wiki-ingest                     # raw/ 폴더 전체 일괄 수집
```

### 옵션

| 옵션 | 설명 |
|------|------|
| `<file>` | 단일 파일 수집 (예: `raw/my-article.md`) |
| `--from <folder>` | `raw/` 대신 다른 폴더를 소스로 사용 |
| `--to <folder>` | 원본을 PARA 구조 하위 폴더에 복사 |
| `--no-copy` | 원본 복사 생략 (`--to`와 함께 사용 불가) |
| `--force-new` | 중복 슬러그도 새 항목으로 강제 생성 |
| `--force-update` | 중복 슬러그를 기존 항목에 덮어쓰기 |
| `--no-interview` | 온톨로지 Context Interview 건너뜀 |
| `--batch-defaults` | 일괄 수집 시 첫 파일 인터뷰 답변을 이후 파일에 재사용 |
| `--summary-only` | 전체 변환 없이 요약 및 메타데이터만 추출 |

### 지원 파일 형식

`.md`, `.txt` — 직접 처리  
`.pdf`, `.docx`, `.pptx`, `.xlsx` — `raw/`에 넣으면 자동 변환 후 수집

### 수집 전략

| 조건 | 전략 |
|------|------|
| `--summary-only` 플래그 | 요약만 추출 |
| `.xlsx` / `.xls` | 요약만 추출 |
| `.pptx` / `.ppt` | 요약만 추출 |
| `.pdf` 30페이지 초과 | 요약만 추출 |
| 그 외 모든 파일 | 전체 내용 처리 |

### 중복 처리

`wiki/history.json`에서 슬러그 중복을 먼저 확인합니다:

- **`--force-new`**: 오늘 날짜를 붙여 새 항목 생성 (예: `my-article-20260421`)
- **`--force-update`**: 기존 항목 덮어쓰기
- **플래그 없을 때 중복 발견**: 업데이트 / 새 항목 / 취소 중 선택 요청
- **삭제된 슬러그**: 신규 수집으로 처리 (슬러그 재사용, `status: "active"` 설정)

### 수집 후 자동 처리 항목

1. `wiki/sources/<slug>.md` — 소스 요약 페이지 생성
2. `wiki/originals/<slug>.md` — 원본 보관
3. `wiki/index.md` — 카탈로그 갱신 (카테고리 분류)
4. `wiki/overview.md` — 전체 요약 갱신
5. `wiki/entities/` — 관련 엔티티 페이지 생성/갱신
6. `wiki/concepts/` — 관련 개념 페이지 생성/갱신
7. `wiki/history.json` — 수집 레지스트리 갱신
8. `wiki/log.md` — 변경 이력 추가

### 인덱스 카테고리 분류 기준

| 카테고리 | 내용 |
|----------|------|
| `기술/개발` | 코드, 도구, API, 프로그래밍, 소프트웨어, 하드웨어, 개발 워크플로 |
| `업무/프로젝트` | 업무 회의, 직장 메모, 회사 프로젝트, 커리어 |
| `개인/생활` | 계정, ID, 비밀번호, 주소, 가족, 금융, 가정 |
| `여행` | 여행 계획, 트레킹, 교통, 숙박, 장소 |
| `임시메모` | 의미 있는 단어 10개 미만, 단편 스니펫, 모호한 컨텍스트 |

---

## /wiki-query — 지식 검색

위키 전체를 읽고 질문에 대한 답변을 합성합니다.

```
/wiki-query 주요 소스들의 공통 테마는?
/wiki-query Claude API 프롬프트 캐싱 방법은?
```

### 동작 방식

1. `wiki/synthesis-map.md`에서 관련 기존 합성물 탐색
2. `wiki/index.md`를 읽어 관련 페이지 파악
3. 관련 페이지 최대 10개 읽기
4. 요약이 부족하면 `source_file` 원본까지 읽기
5. `[[PageName]]` 위키링크 인용을 포함한 마크다운 답변 제공
6. `## Sources` 섹션에 참조 페이지 목록 출력
7. `💾 이 답변을 저장하려면: /wiki-synthesize` 안내 출력

### 고급 필터

구조적 필터(`class:`, `type:`, `AND/OR/NOT`, `context.phase` 같은 점 표기 필드 경로)는 `references/query-advanced.md`를 참조하세요.

---

## /wiki-synthesize — 검색 결과 저장

가장 최근 `/wiki-query` 답변을 재사용 가능한 합성물 페이지로 저장합니다.

```
/wiki-synthesize                        # 자동 슬러그 생성
/wiki-synthesize my-custom-slug         # 슬러그 직접 지정
```

### 동작 방식

1. 현재 세션의 최근 쿼리 질문과 답변을 가져옴
2. 질문에서 kebab-case 슬러그 생성 (또는 지정 슬러그 사용)
3. 답변에서 엔티티, 개념, 관계 추출
4. `wiki/syntheses/<slug>.md` 작성
5. `wiki/synthesis-map.md`에 항목 추가 (추가 전용)
6. `wiki/log.md`에 이력 추가
7. 출력: `✅ Saved synthesis: [[syntheses/<slug>]]`

> 세션 내에 쿼리가 없으면: *"No query found in this session. Run `/wiki-query <question>` first."*

---

## /wiki-lint — 위키 건강 검사

```
/wiki-lint
```

또는 Python 스크립트로:

```bash
python scripts/lint.py
python scripts/lint.py --save   # wiki/lint-report.md에 저장
```

### 검사 항목

| 항목 | 설명 |
|------|------|
| **고아 페이지** | 인바운드 `[[링크]]`가 없는 페이지 |
| **깨진 링크** | 존재하지 않는 페이지를 가리키는 `[[위키링크]]` |
| **누락 엔티티 페이지** | 3개 이상 페이지에서 언급되지만 전용 엔티티 페이지가 없는 이름 |
| **모순** | 소스 간 상충하는 주장 교차 검증 |
| **오래된 요약** | `last_updated`가 관련 개념/엔티티 페이지보다 오래된 소스 페이지 |
| **데이터 공백** | 위키가 답할 수 없는 질문과 필요한 소스 유형 제안 |

`wiki/ontology.yaml`이 있을 경우 온톨로지 관련 추가 검사(7~12개 항목)도 실행됩니다.

검사 완료 후 `wiki/lint-report.md`에 저장할지 물어봅니다.

---

## /wiki-graph — 지식 그래프 시각화

위키 페이지와 위키링크 연결을 인터랙티브 HTML 그래프로 시각화합니다.

```
/wiki-graph
```

또는 Python 스크립트로:

```bash
python scripts/build_graph.py --open          # 재빌드 후 브라우저 열기
python scripts/build_graph.py --report --save  # 보고서 포함 저장
```

출력: `graph/graph.json` + `graph/graph.html` (vis.js 기반, 완전 독립 실행형)

### 노드 색상

| 타입 | 색상 |
|------|------|
| `source` (소스) | #4CAF50 (녹색) |
| `entity` (엔티티) | #2196F3 (파란색) |
| `concept` (개념) | #FF9800 (주황색) |
| `synthesis` (합성물) | #9C27B0 (보라색) |

---

## /wiki-sources — 수집 이력 조회

수집된 모든 소스의 현황을 테이블로 출력합니다.

```
/wiki-sources
```

출력 형식:

| Slug | Title | Ingested | Last Updated | Status |
|------|-------|----------|--------------|--------|

각 활성 소스에 대해 생성된 페이지, 엔티티, 개념 수도 함께 표시됩니다.

---

## /wiki-update — 소스 페이지 갱신

기존 소스를 다시 처리하여 소스 페이지, 엔티티, 개념을 갱신합니다.

```
/wiki-update my-article
```

원본을 재보관하지 않고 소스 페이지를 덮어쓰며, 엔티티/개념 페이지는 병합 방식으로 갱신됩니다.

---

## /wiki-delete — 소스 페이지 삭제

소스 페이지와 해당 소스에서만 참조되는 고아 엔티티/개념 페이지를 삭제합니다.

```
/wiki-delete my-article
```

삭제 전에 삭제 대상 목록을 보여주고 확인을 요청합니다. `wiki/history.json`에는 감사 추적을 위해 항목이 유지되며 `status: "deleted"`로 표시됩니다.

삭제 후 `/wiki-lint`로 남은 깨진 링크를 확인하세요.

---

## /wiki-ontology — 온톨로지 관리

온톨로지는 선택 기능입니다. `wiki/ontology.yaml`이 없으면 모든 명령어가 기본 방식으로 동작합니다.

| 명령어 | 설명 |
|--------|------|
| `/wiki-ontology-init` | 대화형 인터뷰로 `wiki/ontology.yaml` 생성 |
| `/wiki-ontology-show` | 현재 온톨로지 구조와 클래스 목록 출력 |
| `/wiki-ontology-validate` | 위키 페이지와 온톨로지 스키마 정합성 검사 |

온톨로지를 정의하면 수집 시 Context Interview가 실행되고, 엔티티/개념 페이지에 클래스 및 속성 메타데이터가 자동으로 추가됩니다. 그래프 시각화에서도 타입별 색상 구분과 단계(phase) 레인이 활성화됩니다.

자세한 내용은 `references/ontology-commands.md`를 참조하세요.

---

## 페이지 형식

모든 위키 페이지는 아래 프런트매터 형식을 사용합니다:

```yaml
---
title: "페이지 제목"
type: source | entity | concept | synthesis
tags: []
sources: []            # 이 페이지와 관련된 소스 슬러그 목록
last_updated: YYYY-MM-DD
---
```

페이지 간 연결은 `[[PageName]]` 위키링크를 사용합니다.

### 네이밍 규칙

| 타입 | 위치 | 네이밍 |
|------|------|--------|
| 소스 | `wiki/sources/` | `kebab-case.md` |
| 엔티티 | `wiki/entities/` | `TitleCase.md` |
| 개념 | `wiki/concepts/` | `TitleCase.md` |
| 합성물 | `wiki/syntheses/` | `kebab-case.md` |

---

## Python 스크립트

모든 스크립트는 **위키 프로젝트 루트**에서 실행해야 합니다.

```bash
# 마크다운 아닌 파일을 수집 전에 변환
python scripts/file_to_markdown.py --input_dir raw/

# 위키 건강 검사
python scripts/lint.py
python scripts/lint.py --save

# 지식 그래프 생성
python scripts/build_graph.py --open
python scripts/build_graph.py --report --save
```

---

## 주의사항

- **`raw/`는 드롭존** — 수집 후에도 파일이 그대로 남아 있습니다 (원본은 `wiki/originals/`로 복사됨)
- **`wiki/originals/`는 읽기 전용** — 수집 후 절대 수정하지 마세요
- **`wiki/index.md`를 항상 최신 상태로** — 인덱스가 오래되면 `/wiki-query`가 제대로 동작하지 않습니다
- **`wiki/log.md`는 추가 전용** — 과거 항목은 절대 편집하지 마세요
- **`wiki/synthesis-map.md`는 추가 전용** — 과거 항목은 절대 편집하지 마세요
- **위키링크는 대소문자 구분** — `[[OpenAI]]`와 `[[Openai]]`는 다른 페이지입니다
- **소스 슬러그는 파일명과 일치** — `sources:` 프런트매터의 슬러그는 확장자 없는 소스 파일명과 정확히 일치해야 합니다
- **스크립트는 프로젝트 루트에서 실행** — `scripts/` 디렉터리 안에서 실행하면 경로 오류가 발생합니다
- **`graph/graph.html`은 독립 실행형** — JSON이 인라인으로 포함되어 있어 별도 파일 없이 열립니다

---

## 확장 — WiKi-Hub

다른 사람의 위키를 현재 프로젝트에 병합할 수 있는 **WiKi-Hub** 스킬도 있습니다.

- **GitHub:** [godstale/WiKi-Hub](https://github.com/godstale/WiKi-Hub)
- **설치:** `npx skills add godstale/wiki-hub`

---

## 라이선스

MIT
