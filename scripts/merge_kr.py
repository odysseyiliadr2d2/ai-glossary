"""해외 논문에 한글 제목(title_ko)과 region=intl을 붙이고, 국내 논문(out_g*.json)을 region=kr로 추가한다.
국내 논문은 용어당 최대 2편, 해외 논문과 URL이 겹치면 건너뛴다. 여러 번 실행해도 결과가 같다."""
import json, glob, os, re, collections

HERE = os.path.dirname(os.path.abspath(__file__))
TERMS = os.path.join(HERE, "..", "site", "data", "terms.json")
OK_HOSTS = ("kci.go.kr", "riss.kr", "dbpia.co.kr", "scienceon.kisti.re.kr", "koreascience.kr", "koreascience.or.kr",
            "kiss.kstudy.com", "doi.org", "earticle.net", "kiss.kstudy.com", "jksci.org", "ksci.re.kr")

titles_ko = {}
p = os.path.join(HERE, "titles_ko.json")
if os.path.exists(p):
    titles_ko = json.load(open(p, encoding="utf-8"))

kr_ko = {}
p2 = os.path.join(HERE, "kr_titles_ko.json")
if os.path.exists(p2):
    kr_ko = json.load(open(p2, encoding="utf-8"))

kr = {}
for f in sorted(glob.glob(os.path.join(HERE, "out_g*.json"))):
    try:
        for k, v in json.load(open(f, encoding="utf-8")).items():
            kr.setdefault(k, []).extend(v or [])
    except Exception as e:
        print("읽기 실패", f, e)

def ok_url(u):
    return isinstance(u, str) and re.match(r"^https?://[^\s]+$", u) is not None

terms = json.load(open(TERMS, encoding="utf-8"))
st = collections.Counter()
for t in terms:
    intl = [p for p in t["papers"] if p.get("region", "intl") == "intl"]
    for p in intl:
        p["region"] = "intl"
        p["title_ko"] = (titles_ko.get(p["url"]) or p.get("title_ko") or p["title"]).strip()
        if p["title_ko"] == p["title"]: st["번역 없음"] += 1
    seen = {p["url"] for p in intl}
    kps = []
    for q in kr.get(t["id"], []):
        u = (q.get("url") or "").strip()
        title = (q.get("title") or "").strip()
        if not ok_url(u) or not title or u in seen:
            st["국내 제외(형식·중복)"] += 1; continue
        seen.add(u)
        y = q.get("year")
        try: y = int(y) if y not in (None, "") else None
        except (TypeError, ValueError): y = None
        kps.append({"title": title, "title_ko": kr_ko.get(u, title), "authors": (q.get("authors") or "").strip(), "year": y,
                    "venue": (q.get("venue") or "").strip(), "url": u, "region": "kr"})
    t["papers"] = kps[:2] + intl
    st["국내"] += len(kps[:2]); st["해외"] += len(intl)

json.dump(terms, open(TERMS, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
uniq = {r: len({p["url"] for t in terms for p in t["papers"] if p["region"] == r}) for r in ("kr", "intl")}
print(dict(st), "고유:", uniq)
