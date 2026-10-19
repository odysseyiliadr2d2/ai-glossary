# 용어별 출처·관련 논문 조사 규격

입력 파일의 용어마다 **출처(sources)** 와 **관련 논문(papers)** 을 찾는다.
가장 중요한 규칙: **실제로 존재하고 확인한 URL만 쓴다. 추측해서 만든 URL·제목·저자·연도는 절대 넣지 않는다.**
확인 방법: WebSearch 결과에 그 URL이 나왔거나, WebFetch로 열어 제목이 맞는 것을 봤을 때만 "확인"이다.
확인 못 하면 그 항목은 넣지 않는다(빈 배열도 괜찮다).

## 출력: JSON 객체 하나 (UTF-8, 유효한 JSON) — 용어 id를 키로

```json
{
  "rag": {
    "sources": [
      {"title": "What is RAG? - Retrieval-Augmented Generation Explained", "url": "https://aws.amazon.com/what-is/retrieval-augmented-generation/", "publisher": "AWS", "type": "guide"},
      {"title": "Retrieval-augmented generation", "url": "https://en.wikipedia.org/wiki/Retrieval-augmented_generation", "publisher": "Wikipedia", "type": "encyclopedia"}
    ],
    "papers": [
      {"title": "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks", "authors": "Lewis et al.", "year": 2020, "venue": "NeurIPS 2020", "url": "https://arxiv.org/abs/2005.11401"}
    ]
  }
}
```

### sources (용어마다 1~3건)
- 우선순위: ① 공식 문서·표준·정부/규제기관 원문(법령, 금융위·과기정통부 보도자료, EU 공식 사이트, 프로토콜 공식 사이트) ② 주요 기술 기업·연구소의 개념 설명 페이지(Google, Microsoft, AWS, IBM, NVIDIA, Hugging Face 문서 등) ③ Wikipedia(영문 또는 한국어).
- `type`: `official`(공식 원문·표준·법령) | `docs`(제품/라이브러리 공식 문서) | `guide`(기업·기관의 개념 설명) | `encyclopedia`(위키백과 등) | `article`(신뢰할 만한 기사·블로그) 중 하나.
- `title`은 페이지의 실제 제목(줄여도 되지만 지어내지 않는다). `publisher`는 발행처 이름.
- 개인 블로그·광고성 페이지·로그인 필요한 페이지·PDF 직링크(공식 원문 제외)는 피한다.

### papers (용어마다 0~3편)
- 그 개념을 **처음 제안했거나 대표하는** 논문 위주. 개념이 논문에서 나오지 않은 용어(비즈니스·규제·일반 용어)는 빈 배열.
- `url`은 arXiv abs 페이지(`https://arxiv.org/abs/<id>`), ACL Anthology, 학회 공식 페이지, DOI(`https://doi.org/...`) 중 하나.
- `authors`: 제1저자 성 + "et al."(2인이면 두 성), `year`: 숫자, `venue`: 학회/저널(모르면 "arXiv").
- 같은 논문을 여러 용어에 걸어도 된다(예: Transformer 논문).

## 진행
1. 입력의 용어를 차례로 처리한다. 잘 알려진 개념이라도 URL은 검색으로 확인한다. 검색 한 번에 여러 용어를 확인할 수 있으면 묶어서 효율적으로 한다.
2. 결과를 지정된 출력 파일에 저장하고, `python3 -c "import json;d=json.load(open('<파일>'));print(len(d))"`로 유효성·개수를 확인한다. 입력의 모든 id가 키로 있어야 한다(찾은 게 없으면 `{"sources": [], "papers": []}`).
3. 마지막 보고: 용어 수, 출처 총 건수, 논문 총 편수, 출처를 못 찾은 용어 목록만 짧게.
