"""refs/out_*.json(분야별 출처·논문 조사 결과)를 site/data/terms.json에 합친다.
- 없는 분야·용어는 빈 목록
- URL 형식·필드 정리, 같은 URL 중복 제거, 출처 3건·논문 3편까지
"""
import json, glob, os, re, collections

ROOT = os.path.dirname(os.path.abspath(__file__))
TERMS = os.path.join(ROOT, "..", "site", "data", "terms.json")
TYPES = {"official", "docs", "guide", "encyclopedia", "article"}

found = {}
for f in sorted(glob.glob(os.path.join(ROOT, "out_*.json"))):
    try:
        found.update(json.load(open(f, encoding="utf-8")))
    except Exception as e:
        print("읽기 실패", f, e)

def ok_url(u):
    return isinstance(u, str) and re.match(r"^https?://[^\s]+$", u) is not None

terms = json.load(open(TERMS, encoding="utf-8"))
stats = collections.Counter()
for t in terms:
    r = found.get(t["id"], {})
    srcs, seen = [], set()
    for s in r.get("sources", []) or []:
        u = (s.get("url") or "").strip()
        if not ok_url(u) or u in seen or not s.get("title"):
            stats["출처 제외"] += 1; continue
        seen.add(u)
        typ = s.get("type") if s.get("type") in TYPES else "guide"
        srcs.append({"title": s["title"].strip(), "url": u, "publisher": (s.get("publisher") or "").strip(), "type": typ})
    paps, seenp = [], set()
    for p in r.get("papers", []) or []:
        u = (p.get("url") or "").strip()
        if not ok_url(u) or u in seenp or not p.get("title"):
            stats["논문 제외"] += 1; continue
        seenp.add(u)
        y = p.get("year")
        try: y = int(y) if y not in (None, "") else None
        except (TypeError, ValueError): y = None
        paps.append({"title": p["title"].strip(), "authors": (p.get("authors") or "").strip(), "year": y,
                     "venue": (p.get("venue") or "arXiv").strip(), "url": u})
    t["sources"], t["papers"] = srcs[:3], paps[:3]
    stats["출처"] += len(t["sources"]); stats["논문"] += len(t["papers"])
    if t["id"] in found: stats["조사 완료 용어"] += 1
    if not t["sources"]: stats["출처 없는 용어"] += 1

json.dump(terms, open(TERMS, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(dict(stats), "/ 전체", len(terms))
