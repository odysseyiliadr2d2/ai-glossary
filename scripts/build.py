"""실무 AI 용어집 빌드.

data/*.json(원본) → index.html(공개 사이트), build/artifact.html(Claude 미리보기),
supabase/sync-payload.json(Supabase 동기화 데이터), 그리고 --pdf 옵션이면 ai-glossary.pdf.

사용법
  python3 scripts/build.py                 # 검증 + 사이트 + 동기화 payload
  python3 scripts/build.py --pdf           # 위 + PDF 재생성
"""
import json, os, sys, argparse, re, collections, subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
BUILD = os.path.join(ROOT, "build")
SITE_URL = "https://odysseyiliadr2d2.github.io/ai-glossary/"
SUPABASE = {"url": "https://keqatughczjqhnubkydy.supabase.co", "key": "sb_publishable_DlZV7muab9bvGUiUNWh3gA_RTX9Y6MW"}
FIELDS = ["id", "ko", "en", "abbr", "cat", "topic", "level", "easy", "deep", "example", "related",
          "added", "updated", "revision", "status", "sources", "papers"]
SRC_TYPES = {"official", "docs", "guide", "encyclopedia", "article"}
TYPES = {"added", "updated", "moved", "removed"}
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def load(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as f:
        return json.load(f)


def validate(terms, tree, changes, releases):
    """원본 데이터 정합성 검사. 문제가 있으면 목록을 돌려준다(비어 있으면 통과)."""
    errs = []
    ids = [t["id"] for t in terms]
    dup = [i for i, n in collections.Counter(ids).items() if n > 1]
    if dup: errs.append(f"중복 id: {dup}")
    idset = set(ids)
    topic_cat = {tp["id"]: c["id"] for c in tree for tp in c["topics"]}
    in_tree = collections.Counter(i for c in tree for tp in c["topics"] for i in tp["terms"])
    for t in terms:
        miss = [k for k in FIELDS if k not in t]
        if miss: errs.append(f"{t['id']}: 필드 누락 {miss}"); continue
        if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", t["id"]): errs.append(f"{t['id']}: id 형식")
        if t["topic"] not in topic_cat: errs.append(f"{t['id']}: 없는 주제 {t['topic']}")
        elif topic_cat[t["topic"]] != t["cat"]: errs.append(f"{t['id']}: 주제 {t['topic']}가 분야 {t['cat']}에 속하지 않음")
        if t["level"] not in (1, 2, 3): errs.append(f"{t['id']}: level")
        if t["status"] not in ("active", "removed"): errs.append(f"{t['id']}: status")
        for k in ("added", "updated"):
            if not DATE_RE.match(t[k]): errs.append(f"{t['id']}: {k} 날짜 형식")
        if t["updated"] < t["added"]: errs.append(f"{t['id']}: updated가 added보다 이르다")
        if t["status"] == "active":
            if not t["easy"].strip() or not t["deep"].strip(): errs.append(f"{t['id']}: 설명 비어 있음")
            if in_tree[t["id"]] != 1: errs.append(f"{t['id']}: 트리에 {in_tree[t['id']]}번 등장(정확히 1번이어야 함)")
            topic_terms = next(tp["terms"] for c in tree for tp in c["topics"] if tp["id"] == t["topic"])
            if t["id"] not in topic_terms: errs.append(f"{t['id']}: 자기 주제({t['topic']})의 terms 목록에 없음")
        for s_ in t["sources"]:
            if not str(s_.get("url", "")).startswith(("http://", "https://")) or not s_.get("title"):
                errs.append(f"{t['id']}: 출처 형식(title·url 필요) {s_}")
            if s_.get("type") not in SRC_TYPES: errs.append(f"{t['id']}: 출처 type {s_.get('type')}")
        for p_ in t["papers"]:
            if not str(p_.get("url", "")).startswith(("http://", "https://")) or not p_.get("title"):
                errs.append(f"{t['id']}: 논문 형식(title·url 필요) {p_.get('title')}")
            if p_.get("year") is not None and not isinstance(p_.get("year"), int): errs.append(f"{t['id']}: 논문 year는 숫자")
            if p_.get("region") not in ("kr", "intl"): errs.append(f"{t['id']}: 논문 region은 kr 또는 intl")
            if not p_.get("title_ko"): errs.append(f"{t['id']}: 논문 title_ko(한글 제목) 필요 {p_.get('title')}")
        bad_rel = [r for r in t["related"] if r not in idset]
        if bad_rel: errs.append(f"{t['id']}: 없는 연관 id {bad_rel}")
        if not any(c["id"] == t["id"] for c in changes): errs.append(f"{t['id']}: changelog 기록 없음")
    for i in in_tree:
        if i not in idset: errs.append(f"트리에 없는 문서 id: {i}")
    tids = [tp["id"] for c in tree for tp in c["topics"]]
    if len(tids) != len(set(tids)): errs.append("중복 주제 id")
    for c in changes:
        if c["id"] not in idset: errs.append(f"changelog: 없는 id {c['id']}")
        if c["type"] not in TYPES: errs.append(f"changelog: 종류 {c['type']}")
        if not DATE_RE.match(c["date"]): errs.append(f"changelog: 날짜 {c['date']}")
    for r in releases:
        if not DATE_RE.match(r["date"]): errs.append(f"releases: 날짜 {r['date']}")
    return errs


def nodes_for(terms, tree):
    """Supabase wiki_nodes 행. id 충돌을 피하려고 분야는 c.<코드>, 주제는 t.<주제id>로 둔다."""
    first_day = min(t["added"] for t in terms)
    last_day = max(t["updated"] for t in terms)
    rows = [{"id": "root", "parent_id": None, "kind": "root", "title_ko": "실무 AI 용어집", "title_en": "AI Glossary",
             "description": "실무 AI 용어 위키", "path": "root", "depth": 0, "sort_order": 0,
             "created_on": first_day, "updated_on": last_day, "status": "active"}]
    by_id = {t["id"]: t for t in terms}
    for ci, c in enumerate(tree):
        members = [by_id[i] for tp in c["topics"] for i in tp["terms"] if i in by_id]
        rows.append({"id": f"c.{c['id']}", "parent_id": "root", "kind": "category", "title_ko": c["ko"], "title_en": c["en"],
                     "description": c["desc"], "path": f"root/{c['id']}", "depth": 1, "sort_order": ci,
                     "created_on": min(t["added"] for t in members), "updated_on": max(t["updated"] for t in members), "status": "active"})
        for ti, tp in enumerate(c["topics"]):
            tm = [by_id[i] for i in tp["terms"] if i in by_id]
            rows.append({"id": f"t.{tp['id']}", "parent_id": f"c.{c['id']}", "kind": "topic", "title_ko": tp["ko"], "title_en": tp["en"],
                         "description": tp["desc"], "path": f"root/{c['id']}/{tp['id']}", "depth": 2, "sort_order": ti,
                         "created_on": min(t["added"] for t in tm), "updated_on": max(t["updated"] for t in tm), "status": "active"})
    order = {i: k for c in tree for tp in c["topics"] for k, i in enumerate(tp["terms"])}
    for t in terms:
        rows.append({"id": t["id"], "parent_id": f"t.{t['topic']}", "kind": "page", "title_ko": t["ko"], "title_en": t["en"],
                     "description": t["easy"], "path": f"root/{t['cat']}/{t['topic']}/{t['id']}", "depth": 3,
                     "sort_order": order.get(t["id"], 999), "created_on": t["added"], "updated_on": t["updated"], "status": t["status"]})
    return rows


def sync_payload(terms, tree, changes, releases):
    """wiki_sync()에 넘길 전체 payload. 저장소에 커밋되고, Supabase의 wiki_pull()이 GitHub에서 직접 읽어 적용한다.
    upsert만 쓰므로 몇 번을 다시 적용해도 결과가 같다."""
    return {
        "nodes": nodes_for(terms, tree),
        "pages": [{"node_id": t["id"], "abbr": t["abbr"], "level": t["level"], "easy": t["easy"], "deep": t["deep"],
                   "example": t["example"], "revision": t["revision"], "related": t["related"],
                   "sources": t["sources"], "papers": t["papers"]} for t in terms],
        "revisions": [{"node_id": c["id"], "rev_date": c["date"], "change_type": c["type"], "summary": c["summary"]} for c in changes],
        "releases": releases,
    }


def render(tpl, terms, tree, changes, releases, pdf_meta, for_site):
    j = lambda o: json.dumps(o, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    page = (tpl.replace("/*__DATA__*/[]", j(terms)).replace("/*__TREE__*/[]", j(tree))
               .replace("/*__CHANGES__*/[]", j(changes)).replace("/*__RELEASES__*/[]", j(releases))
               .replace("/*__PDF_META__*/", pdf_meta))
    if for_site:
        page = (page.replace("/*__PDF_URL__*/", "ai-glossary.pdf").replace("/*__PDF_ATTR__*/", 'download="실무-AI-용어집.pdf"')
                    .replace('const STATS = { url: "", key: "" };', f'const STATS = {{ url: "{SUPABASE["url"]}", key: "{SUPABASE["key"]}" }};'))
        head, body = page.split('<div class="wrap">', 1)
        return ('<!doctype html>\n<html lang="ko">\n<head>\n<meta charset="utf-8">\n'
                '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
                + head + '</head>\n<body>\n<div class="wrap">' + body + '\n</body>\n</html>\n')
    return (page.replace("/*__PDF_URL__*/", SITE_URL + "ai-glossary.pdf")
                .replace("/*__PDF_ATTR__*/", 'target="_blank" rel="noopener"'))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", action="store_true", help="PDF도 다시 만든다")
    a = ap.parse_args()

    terms, tree, changes, releases = load("terms.json"), load("tree.json"), load("changelog.json"), load("releases.json")
    errs = validate(terms, tree, changes, releases)
    if errs:
        print("검증 실패:"); [print(" -", e) for e in errs[:50]]; sys.exit(1)
    live = [t for t in terms if t["status"] == "active"]
    print(f"검증 통과: 문서 {len(live)}개(삭제 표시 {len(terms) - len(live)}), 분야 {len(tree)}, 주제 {sum(len(c['topics']) for c in tree)}, 이력 {len(changes)}")

    if a.pdf:
        subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "make_pdf.py")], check=True)

    pdf = os.path.join(ROOT, "ai-glossary.pdf")
    if os.path.exists(pdf):
        from pypdf import PdfReader
        pdf_meta = f"{len(PdfReader(pdf).pages)}쪽 · {os.path.getsize(pdf) / 1024 / 1024:.1f}MB"
    else:
        pdf_meta = "PDF"

    tpl = open(os.path.join(ROOT, "scripts", "template.html"), encoding="utf-8").read()
    os.makedirs(BUILD, exist_ok=True)
    with open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8") as f:
        f.write(render(tpl, terms, tree, changes, releases, pdf_meta, True))
    with open(os.path.join(BUILD, "artifact.html"), "w", encoding="utf-8") as f:
        f.write(render(tpl, terms, tree, changes, releases, pdf_meta, False))

    payload = sync_payload(terms, tree, changes, releases)
    os.makedirs(os.path.join(ROOT, "supabase"), exist_ok=True)
    with open(os.path.join(ROOT, "supabase", "sync-payload.json"), "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
    print(f"사이트: index.html · 미리보기: build/artifact.html · PDF: {pdf_meta}")
    print(f"동기화 payload: supabase/sync-payload.json (노드 {len(payload['nodes'])}, 문서 {len(payload['pages'])}, 이력 {len(payload['revisions'])})")
    print("push 후 Supabase에서 실행: select public.wiki_pull();")


if __name__ == "__main__":
    main()
