# 실무 AI 용어집

AX 전환을 함께 하는 실무자와 개발자를 위한 AI 용어 위키다. 같은 용어를 **입문**(비개발자)과 **심화**(구현자) 두 수준으로 설명한다.

**사이트**: https://odysseyiliadr2d2.github.io/ai-glossary/

- 위키 트리: 분야(11) › 주제(60) › 문서(422)
- 문서마다 입문·심화 설명, 실무 예시, 출처·더 읽을거리, 관련 논문, 연관 문서, 이 문서를 가리키는 문서, 문서 이력
- 논문 화면: 연결된 논문 검색(제목·저자·학회·연도·용어), 연도·분야 필터, arXiv·Semantic Scholar·Google Scholar·RISS 바로가기
- 날짜별 변경 타임라인, 초성·ABC 색인, 검색(한글·영문·약어·초성)
- 방문자가 많이 찾은 문서 순위 (Supabase 집계)
- 전체 용어 PDF (분야별 차례, 가나다순 본문, 가나다·ABC 색인)
- 2주마다 월요일 오전 정기 업데이트 → [UPDATE_GUIDE.md](UPDATE_GUIDE.md)

## 구조

| 경로 | 내용 |
|---|---|
| `data/terms.json` | 문서 원본 (용어별 설명, 분야·주제, 추가·수정일, 판, 상태) |
| `data/tree.json` | 위키 트리 (분야 › 주제, 주제별 읽는 순서) |
| `data/changelog.json` | 문서별 변경 이력 (타임라인의 원본) |
| `data/releases.json` | 업데이트 회차별 제목·요약 |
| `scripts/build.py` | 검증 → `index.html`, `ai-glossary.pdf`, `supabase/sync-payload.json` 생성 |
| `scripts/template.html` | 사이트 화면 |
| `scripts/make_pdf.py` | PDF 생성 (Chromium 인쇄, 쪽번호 색인) |
| `supabase/schema.sql` | Supabase 테이블·뷰·함수 구조 |
| `supabase/sync-payload.json` | Supabase 동기화 데이터 (빌드 산출물) |
| `index.html`, `ai-glossary.pdf` | GitHub Pages로 공개되는 결과물 |

## 고치는 법

`data/`만 고치고 `python3 scripts/build.py --pdf`를 실행한 뒤 커밋·푸시한다. Supabase에는 `select public.wiki_pull();`로 반영한다.

## Supabase

| 객체 | 내용 |
|---|---|
| `wiki_nodes` | 트리 노드 (root › category › topic › page), `path`·`depth`·`sort_order`·`status` |
| `wiki_pages` | 문서 본문, `related`(연관 문서 id 배열), `sources`·`papers`(jsonb) |
| `wiki_papers` (뷰) | 문서별 관련 논문을 한 줄씩 펼친 논문 검색용 뷰 |
| `wiki_sources` (뷰) | 문서별 출처를 한 줄씩 펼친 뷰 |
| `wiki_revisions` | 날짜별 변경 이력 |
| `wiki_releases` | 회차별 요약 |
| `wiki_tree` (뷰) | 재귀로 펼친 트리와 breadcrumb |
| `wiki_timeline` (뷰) | 날짜별 변경 묶음 |
| `wiki_backlinks` (뷰) | 문서 링크 그래프 |
| `term_hits` | 문서별 조회수 |

방문자는 읽기와 조회수 +1만 할 수 있다. 쓰기는 `wiki_sync`/`wiki_pull`(관리자 전용)로만 한다.

## 브랜치

| 브랜치 | 내용 |
|---|---|
| `main` | 공개 사이트(GitHub Pages). 학습 카드형 디자인 |
| `design/v1-newsletter` | 이전 디자인(뉴스레터형 네이비·앰버 카드) 보존본 |

## 기준일

규제·정책 관련 문서는 각 문서의 "마지막 수정" 날짜 기준이다.
