# 정기 업데이트 절차 (격주 월요일)

이 문서는 2주마다 실행되는 예약 작업이 따르는 절차다. 사람이 손으로 업데이트할 때도 같은 순서를 따른다.
**검토 없이 바로 공개되는 방식**이므로, 아래 품질 기준을 지키지 못한 변경은 반영하지 않는다.

## 0. 준비
- 저장소: `odysseyiliadr2d2/ai-glossary` (기본 브랜치 `main`)
- Supabase 프로젝트: `ai-glossary` (id `keqatughczjqhnubkydy`)
- 오늘 날짜(KST)를 `TODAY`(YYYY-MM-DD)로 정한다.
- 이번 회차가 실행 주차인지 확인한다: 기준일 2026-10-19(월)부터 14일 간격의 월요일만 실행한다.
  `(TODAY - 2026-10-19).days % 14 == 0` 이 아니면 아무것도 바꾸지 않고 "이번 주는 쉬는 주"라고 남기고 끝낸다.

## 1. 조사 (최근 2주)
웹 검색으로 직전 회차 이후 2주간의 AI 동향을 훑는다. 공식 발표·논문·정부/규제기관 자료를 우선한다.
- **새 용어 후보**: 실무자·개발자가 앞으로 자주 듣게 될 용어. 일회성 제품명·마케팅 신조어는 제외한다.
- **기존 문서 갱신 후보**: 사실이 바뀐 문서. 특히 규제·정책(`safety`의 법·규제 주제, `biz`의 망분리 등),
  프로토콜·표준(MCP, A2A 등), 시행일·버전·수치가 들어간 문서.
- 한 회차 목표: 새 용어 **3~10개**, 갱신 **0~10개**. 확신이 없으면 넣지 않는다.

## 2. 데이터 수정 (`data/`만 고친다)
### 새 용어 → `data/terms.json`에 항목 추가
```json
{"id":"kebab-case-영문","ko":"한국어 표제어","en":"English Name","abbr":"약어 또는 빈 문자열",
 "cat":"분야코드","topic":"주제id","level":1,
 "easy":"비개발자용 1~2문장","deep":"구현자용 2~4문장","example":"실무 예시 한 문장(금융·기업 맥락 권장)",
 "related":["기존 id 2~5개"],"added":"TODAY","updated":"TODAY","revision":1,"status":"active"}
```
- 문체는 간결한 평서형 "~다". 마케팅 문구 금지. 특정 회사 홍보 금지(대표 사례 언급은 가능).
- `cat`·`topic`은 `data/tree.json`에 있는 것만 쓴다. 해당 주제의 `terms` 배열에도 **학습 순서에 맞는 위치**로 id를 넣는다.
- 들어갈 주제가 정말 없을 때만 `tree.json`에 주제를 새로 만든다(id `<분야코드>-<영문>`, 3개 이상 문서가 모일 때).
- 관련 있는 기존 문서 1~3개의 `related`에도 새 id를 추가한다(그 문서는 `updated`를 바꾸지 않는다. 링크 추가는 수정으로 치지 않는다).

### 갱신 → 해당 항목 수정
- 내용이 바뀌면 `updated`를 TODAY로, `revision`을 1 올린다.

### 삭제가 필요하면
- 항목을 지우지 말고 `"status":"removed"`, `updated`=TODAY. 트리의 `terms` 배열에서는 뺀다. 다른 문서의 `related`에서도 뺀다.

### 이력 → `data/changelog.json`에 추가
```json
{"date":"TODAY","id":"용어id","type":"added|updated|removed|moved","summary":"무엇이 바뀌었는지 한 줄"}
```
- 새 용어의 summary는 `"최초 수록"`. 갱신은 바뀐 사실을 구체적으로(예: "EU AI Act 고위험 의무 적용일 2027년 12월로 변경 반영").

### 회차 요약 → `data/releases.json`에 추가
```json
{"date":"TODAY","title":"YYYY년 M월 D일 정기 업데이트","note":"새 용어 N개, 갱신 M개. 이번 회차의 주요 흐름 1~2문장."}
```

## 3. 빌드와 검증
```bash
pip install --break-system-packages pypdf pdfplumber playwright >/dev/null 2>&1 || true
python3 scripts/build.py --pdf
```
- "검증 통과"가 나와야 한다. 실패하면 메시지대로 data를 고쳐 다시 실행한다.
- PDF 렌더에는 Chromium(playwright)과 한글 글꼴(Noto Sans/Serif CJK KR)이 필요하다. PDF만 실패하면 `--pdf` 없이 빌드해 사이트는 반영하고, 보고에 PDF 미갱신을 적는다.
- 새 용어 1개를 골라 `index.html`을 브라우저로 열어 `#<id>` 문서가 정상 표시되는지 확인한다(가능할 때).

## 4. 반영
```bash
git add -A
git commit -m "정기 업데이트 TODAY: 새 용어 N개, 갱신 M개"
git push origin main
```
그다음 Supabase에서(MCP `execute_sql`, 프로젝트 `keqatughczjqhnubkydy`):
```sql
select public.wiki_pull();
```
- raw.githubusercontent.com 캐시 때문에 방금 push한 내용이 안 보이면 커밋 해시로 실행한다: `select public.wiki_pull('<커밋 SHA>');`
- 결과의 `pages` 수가 `data/terms.json` 항목 수와 같은지 확인한다.

## 5. 보고
작업 결과를 짧게 남긴다: 새 용어 목록, 갱신 목록(무엇이 바뀌었는지), 참고한 출처 URL, 사이트·PDF·Supabase 반영 여부, 실패한 단계.
