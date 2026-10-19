# 국내 논문 조사 규격

입력 파일의 AI 용어마다 **한국 학술지·학회에 실린 국내 논문**을 찾는다. 목표: 용어당 평균 1편(0~2편).

## 가장 중요한 규칙
- **WebSearch 결과에 실제로 나온 논문만 쓴다.** 제목·URL은 검색 결과에 나온 그대로. 추측해서 만든 제목·URL·저자·연도는 절대 넣지 않는다.
- **WebFetch(페이지 열기)는 쓰지 않는다.** 사용자에게 승인 창이 뜨기 때문이다. 검색 결과 스니펫만으로 판단한다.
- 웹 검색 한도는 여러 에이전트가 공유한다(전체 약 200회). **너에게 할당된 검색은 최대 45회.** 한 번의 검색으로 여러 용어를 확인할 수 있게 묶어서 검색하라(예: `site:kci.go.kr 트랜스포머 어텐션 딥러닝`).
- 확인 못 한 용어는 빈 배열. 무리해서 관련 없는 논문을 붙이지 않는다.

## 어떤 논문
- 한국 학술지(KCI 등재·후보지 우선) 또는 국내 학회 논문지/학술대회 논문. 저자가 한국 연구자이거나 한국 학술지에 실린 것.
- 용어 개념을 직접 다루거나, 그 기술을 한국어·국내 산업(특히 금융·공공)에 적용한 논문. 최근(2018년 이후) 우선.
- 허용 URL 도메인: kci.go.kr, riss.kr, dbpia.co.kr, scienceon.kisti.re.kr, koreascience.kr(또는 koreascience.or.kr), kiss.kstudy.com, 학회 공식 사이트, doi.org.

## 출력: JSON 객체 (UTF-8) — 용어 id를 키로
```json
{
  "transformer": [
    {"title": "트랜스포머 기반 한국어 금융 문서 분류 모델 연구", "authors": "홍길동 외", "year": 2022,
     "venue": "한국정보과학회논문지", "url": "https://www.kci.go.kr/kciportal/ci/sereArticleSearch/ciSereArtiView.kci?sereArticleSearchBean.artiId=ART000..."}
  ]
}
```
- `title`: 한국어 원제(검색 결과 그대로). 영어로만 나온 국내 논문이면 영어 제목 그대로.
- `authors`: 제1저자 이름 + "외"(2인이면 두 이름). 검색 결과에 없으면 빈 문자열.
- `year`: 숫자, 모르면 null. `venue`: 학술지·학회명, 모르면 빈 문자열.
- 입력의 모든 id가 키로 있어야 한다(없으면 빈 배열).

## 진행
1. 입력 용어를 분야별로 묶어 검색 계획을 세운 뒤 검색한다(45회 이내).
2. 지정된 출력 파일에 저장하고 `python3 -c "import json;d=json.load(open('<파일>'));print(len(d), sum(len(v) for v in d.values()))"`로 확인.
3. 마지막 보고: 용어 수, 찾은 논문 수, 사용한 검색 횟수만 짧게.
