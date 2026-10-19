"""실무 AI 용어집 PDF 생성: 1차 렌더로 각 용어의 쪽번호를 찾고, 2차 렌더에서 색인에 쪽번호를 채운다."""
import json, html, asyncio, re, unicodedata, os
from functools import cmp_to_key
import pdfplumber
from playwright.async_api import async_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TERMS = [t for t in json.load(open(f"{ROOT}/data/terms.json", encoding="utf-8")) if t.get("status", "active") == "active"]
TREE = json.load(open(f"{ROOT}/data/tree.json", encoding="utf-8"))
UPDATED = max(t["updated"] for t in TERMS)
BY_ID = {t["id"]: t for t in TERMS}
CATS = {"basics": "AI 기초·머신러닝", "dl": "딥러닝·신경망", "llm": "LLM·언어모델", "training": "학습·튜닝·정렬",
        "prompt": "프롬프트·추론", "rag": "RAG·검색·데이터", "agent": "AI 에이전트·도구", "genai": "생성 AI·멀티모달",
        "infra": "인프라·배포·LLMOps", "safety": "평가·안전·규제", "biz": "AX·비즈니스 적용"}
LEVELS = {1: "입문", 2: "실무", 3: "심화"}
CHO = "ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ"
BASE = {"ㄲ": "ㄱ", "ㄸ": "ㄷ", "ㅃ": "ㅂ", "ㅆ": "ㅅ", "ㅉ": "ㅈ"}
KO_ORDER = list("ㄱㄴㄷㄹㅁㅂㅅㅇㅈㅊㅋㅌㅍㅎ")
SITE = "odysseyiliadr2d2.github.io/ai-glossary"
DATE = f"{UPDATED[:4]}년 {int(UPDATED[5:7])}월 {int(UPDATED[8:10])}일"
e = html.escape


def initial(s):
    c = s.strip()[0]
    if "가" <= c <= "힣":
        ch = CHO[(ord(c) - 0xAC00) // 588]
        return BASE.get(ch, ch)
    return c.upper() if c.isascii() and c.isalpha() else "#"


def ko_key(s):
    # 한글 음절을 먼저, 그다음 영문, 숫자·기호 순 — 사이트의 Intl.Collator('ko')와 같은 감각
    out = []
    for ch in s:
        if "가" <= ch <= "힣": out.append((1, ord(ch)))
        elif ch.isascii() and ch.isalpha(): out.append((2, ord(ch.lower())))
        elif ch.isdigit(): out.append((0, ord(ch)))
        else: out.append((3, ord(ch)))
    return out


def group_order(k, order):
    return (order.index(k) if k in order else (-1 if k == "#" else 100 + ord(k[0])))


def refs_html(t):
    srcs = t.get("sources") or []
    paps = t.get("papers") or []
    if not srcs and not paps:
        return ""
    parts = []
    if srcs:
        parts.append("출처 " + " · ".join(e(s.get("publisher") or s["url"].split("/")[2]) for s in srcs))
    if paps:
        def cite(p):
            a = f'{p.get("authors") or ""} {p.get("year") or ""}'.strip()
            if not a:
                a = (p.get("venue") or (p.get("title_ko") or p["title"])[:24]).strip()
            return ("[국내] " if p.get("region") == "kr" else "") + a
        parts.append("논문 " + " · ".join(e(cite(p)) for p in paps))
    return f'<div class="refs">{" / ".join(parts)}</div>'


def entry_html(t):
    abbr = f'<b>{e(t["abbr"])}</b> · ' if t["abbr"] and t["abbr"] != t["en"] else ""
    rel = ", ".join(e(BY_ID[r]["ko"]) for r in t["related"] if r in BY_ID)
    ex = f'<div class="d ex"><span>예시</span><p>{e(t["example"])}</p></div>' if t["example"] else ""
    return f'''<article class="entry" id="{t["id"]}">
  <h3><i class="mk">§{t["id"]}§</i>{e(t["ko"])}</h3>
  <div class="en">{abbr}{e(t["en"])}</div>
  <div class="tags">{CATS[t["cat"]]} · <em class="l{t["level"]}">{LEVELS[t["level"]]}</em></div>
  <div class="d easy"><span>입문</span><p>{e(t["easy"])}</p></div>
  <div class="d deep"><span>심화</span><p>{e(t["deep"])}</p></div>
  {ex}
  {f'<div class="rel">연관 {rel}</div>' if rel else ""}
  {refs_html(t)}
</article>'''


def build(pages=None, total=0):
    PAGES = total or "—"
    terms = sorted(TERMS, key=lambda t: ko_key(t["ko"]))
    groups = {}
    for t in terms:
        groups.setdefault(initial(t["ko"]), []).append(t)
    keys = sorted(groups, key=lambda k: group_order(k, KO_ORDER))
    body = "".join(f'<section class="letter-group"><h2 class="letter">{e(k)}</h2>{"".join(entry_html(t) for t in groups[k])}</section>' for k in keys)

    cat_counts = {c: sum(1 for t in TERMS if t["cat"] == c) for c in CATS}
    lv_counts = {l: sum(1 for t in TERMS if t["level"] == l) for l in LEVELS}
    cats_list = "".join(f'<li><span>{n}</span><b>{cat_counts[c]}</b></li>' for c, n in CATS.items())

    def pg(t):
        return str(pages.get(t["id"], "")) if pages else "000"

    # 가나다 색인
    ko_idx = ""
    for k in keys:
        ko_idx += f'<div class="ix-g"><h4>{e(k)}</h4>' + "".join(
            f'<div class="ix-r"><span>{e(t["ko"])}</span><i></i><b>{pg(t)}</b></div>' for t in groups[k]) + "</div>"
    # ABC 색인 (영문 명칭 → 한글)
    en_terms = sorted(TERMS, key=lambda t: t["en"].lower())
    en_groups = {}
    for t in en_terms:
        en_groups.setdefault(initial(t["en"]), []).append(t)
    en_idx = ""
    for k in sorted(en_groups, key=lambda k: (k != "#", k)):
        en_idx += f'<div class="ix-g"><h4>{e(k)}</h4>' + "".join(
            f'<div class="ix-r en"><span>{e(t["en"])}{" (" + e(t["abbr"]) + ")" if t["abbr"] and t["abbr"] != t["en"] else ""}</span><i></i><b>{pg(t)}</b></div>'
            for t in en_groups[k]) + "</div>"

    toc = ""
    for c in TREE:
        toc += f'<div class="toc-c"><h4>{e(c["ko"])}</h4>'
        for tp in c["topics"]:
            ids = [i for i in tp["terms"] if i in BY_ID]
            if not ids: continue
            first = min((int(pg(BY_ID[i]) or 0) for i in ids), default=0) if pages else "000"
            toc += f'<div class="toc-t"><b>{e(tp["ko"])}</b><span class="toc-n">{len(ids)}</span></div><p>' + " · ".join(
                f'{e(BY_ID[i]["ko"])}<small>{pg(BY_ID[i])}</small>' for i in ids) + "</p>"
        toc += "</div>"

    return f'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>실무 AI 용어집</title><style>
@page {{ size: A4; margin: 18mm 15mm 16mm 15mm; }}
@page cover {{ margin: 0; }}
:root {{ --ink:#15201E; --muted:#5B6B67; --rule:#C9D3CF; --accent:#0E6B62; --soft:#E4F0EC;
  --l1:#2F7D3A; --l2:#9A5B00; --l3:#A1314F;
  --serif:"Noto Serif CJK KR", serif; --sans:"Noto Sans CJK KR", sans-serif; --mono:"Noto Sans Mono CJK KR", monospace; }}
* {{ box-sizing: border-box; }}
html {{ -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
body {{ margin:0; font-family:var(--sans); color:var(--ink); font-size:8.6pt; line-height:1.6; word-break:keep-all; overflow-wrap:anywhere; }}

/* 표지 */
.cover {{ page: cover; height:297mm; padding:34mm 24mm 22mm; display:flex; flex-direction:column; break-after:page; background:#F3F5F4; position:relative; }}
.cover::before {{ content:""; position:absolute; left:0; top:0; bottom:0; width:9mm; background:var(--accent); }}
.cover .eyebrow {{ font-size:9pt; letter-spacing:.18em; color:var(--accent); font-weight:700; }}
.cover h1 {{ font-family:var(--serif); font-weight:900; font-size:46pt; line-height:1.15; margin:8mm 0 6mm; letter-spacing:-.01em; }}
.cover .lead {{ font-size:12pt; line-height:1.75; color:var(--muted); max-width:120mm; margin:0; }}
.cover .stats {{ display:flex; gap:14mm; margin:16mm 0 12mm; }}
.cover .stats div b {{ display:block; font-family:var(--serif); font-size:28pt; font-weight:900; color:var(--accent); line-height:1.1; }}
.cover .stats div span {{ font-size:9pt; color:var(--muted); }}
.cover ul {{ list-style:none; padding:0; margin:0; columns:2; column-gap:12mm; max-width:150mm; }}
.cover li {{ display:flex; justify-content:space-between; border-bottom:.4pt solid var(--rule); padding:1.6mm 0; font-size:9.5pt; break-inside:avoid; }}
.cover li b {{ font-family:var(--mono); font-weight:400; color:var(--muted); }}
.cover .how {{ margin-top:auto; display:grid; grid-template-columns:repeat(3,1fr); gap:6mm; font-size:8.6pt; color:var(--muted); }}
.cover .how strong {{ display:block; font-size:9.5pt; color:var(--ink); margin-bottom:1mm; }}
.cover .how .l1 strong {{ color:var(--l1); }} .cover .how .l2 strong {{ color:var(--l2); }} .cover .how .l3 strong {{ color:var(--l3); }}
.cover .foot {{ margin-top:10mm; padding-top:4mm; border-top:.6pt solid var(--ink); display:flex; justify-content:space-between; font-size:8.6pt; color:var(--muted); }}
.cover .foot b {{ font-family:var(--mono); font-weight:400; color:var(--ink); }}

/* 본문: 2단 사전 */
.body {{ columns:2; column-gap:8mm; column-rule:.4pt solid var(--rule); }}
.letter {{ font-family:var(--serif); font-weight:900; font-size:26pt; line-height:1; color:var(--accent); margin:2mm 0 1mm; break-after:avoid; }}
.letter-group + .letter-group .letter {{ margin-top:5mm; }}
.entry {{ break-inside:avoid; padding:2.4mm 0 2.8mm; border-bottom:.4pt solid var(--rule); }}
.entry h3 {{ font-family:var(--serif); font-weight:700; font-size:11.5pt; line-height:1.35; margin:0; break-after:avoid; }}
.mk {{ font-size:1pt; color:#fff; font-style:normal; }}
.en {{ font-family:var(--mono); font-size:7.6pt; color:var(--muted); line-height:1.4; }}
.en b {{ color:var(--ink); font-weight:500; }}
.tags {{ font-size:7.2pt; color:var(--accent); margin:.6mm 0 1.2mm; }}
.tags em {{ font-style:normal; font-weight:700; }}
.tags .l1 {{ color:var(--l1); }} .tags .l2 {{ color:var(--l2); }} .tags .l3 {{ color:var(--l3); }}
.d {{ display:grid; grid-template-columns:7.5mm 1fr; gap:1.5mm; margin-top:.8mm; }}
.d span {{ font-size:6.6pt; font-weight:700; padding-top:.5mm; letter-spacing:.04em; }}
.d.easy span {{ color:var(--l1); }} .d.deep span {{ color:var(--l3); }} .d.ex span {{ color:var(--accent); }}
.d p {{ margin:0; }}
.d.ex p {{ color:var(--muted); }}
.rel {{ font-size:7.2pt; color:var(--muted); margin-top:1mm; }}
.refs {{ font-size:6.8pt; color:var(--muted); margin-top:.6mm; font-style:italic; }}

/* 분야별 차례 */
.toc {{ break-after:page; }}
.toc h2 {{ font-family:var(--serif); font-weight:900; font-size:22pt; margin:0 0 1mm; }}
.toc .sub {{ color:var(--muted); font-size:8.4pt; margin:0 0 5mm; }}
.toc-cols {{ columns:2; column-gap:8mm; }}
.toc-c {{ break-inside:avoid-column; margin-bottom:4mm; }}
.toc-c h4 {{ font-family:var(--serif); font-size:12.5pt; color:var(--accent); margin:0 0 1mm; border-bottom:.6pt solid var(--ink); padding-bottom:.6mm; }}
.toc-t {{ display:flex; justify-content:space-between; font-size:8.4pt; margin-top:1.2mm; }}
.toc-t .toc-n {{ font-family:var(--mono); color:var(--muted); font-size:7.4pt; }}
.toc-c p {{ margin:.3mm 0 0; font-size:7.4pt; line-height:1.55; color:var(--ink); }}
.toc-c p small {{ font-family:var(--mono); color:var(--muted); font-size:6.4pt; margin-left:.8mm; }}

/* 색인 */
.index {{ break-before:page; }}
.index h2 {{ font-family:var(--serif); font-weight:900; font-size:22pt; margin:0 0 1mm; }}
.index .sub {{ color:var(--muted); font-size:8.4pt; margin:0 0 5mm; }}
.index + .index {{ }}
.ix {{ columns:3; column-gap:7mm; }}
.ix-g {{ break-inside:avoid-column; margin-bottom:3mm; }}
.ix-g h4 {{ font-family:var(--serif); font-size:12pt; color:var(--accent); margin:0 0 .6mm; break-after:avoid; }}
.ix-r {{ display:flex; align-items:baseline; gap:1.5mm; font-size:7.6pt; line-height:1.55; break-inside:avoid; }}
.ix-r span {{ flex:0 1 auto; }}
.ix-r i {{ flex:1 1 auto; border-bottom:.5pt dotted var(--rule); min-width:3mm; transform:translateY(-.8mm); }}
.ix-r b {{ font-family:var(--mono); font-weight:400; color:var(--muted); font-variant-numeric:tabular-nums; }}
.ix-r.en span {{ font-family:var(--mono); font-size:7pt; }}
</style></head><body>
<section class="cover">
  <div class="eyebrow">AI GLOSSARY · {DATE} 기준</div>
  <h1>실무 AI 용어집</h1>
  <p class="lead">AX 전환을 함께 하는 실무자와 개발자를 위해, 같은 용어를 입문과 심화 두 수준으로 풀었다. 용어마다 실무 예시와 연관 용어를 함께 달았다.</p>
  <div class="stats">
    <div><b>{len(TERMS)}</b><span>용어</span></div>
    <div><b>{len(TREE)}</b><span>분야</span></div><div><b>{sum(len(c["topics"]) for c in TREE)}</b><span>주제</span></div>
    <div><b>{PAGES}</b><span>쪽</span></div>
  </div>
  <ul>{cats_list}</ul>
  <div class="how">
    <div class="l1"><strong>입문 · {lv_counts[1]}개</strong>누구나 알아야 할 기본 용어</div>
    <div class="l2"><strong>실무 · {lv_counts[2]}개</strong>업무에 AI를 적용하는 사람의 용어</div>
    <div class="l3"><strong>심화 · {lv_counts[3]}개</strong>기술을 구현하는 사람의 용어</div>
  </div>
  <div class="foot"><span>분야별 차례 다음에 가나다순 본문, 뒤쪽에 가나다·ABC 색인이 있다.</span><b>{SITE}</b></div>
</section>
<section class="toc"><h2>분야별 차례</h2><p class="sub">위키 트리(분야 › 주제 › 문서)를 읽는 순서대로 펼쳤다. 숫자는 수록 쪽이다.</p><div class="toc-cols">{toc}</div></section>
<main class="body">{body}</main>
<section class="index"><h2>가나다 색인</h2><p class="sub">한글 표제어와 수록 쪽</p><div class="ix">{ko_idx}</div></section>
<section class="index"><h2>ABC 색인</h2><p class="sub">영문 명칭(약어)으로 한글 표제어 쪽을 찾는다</p><div class="ix">{en_idx}</div></section>
</body></html>'''


FOOTER = f'''<div style="width:100%;font-family:'Noto Sans CJK KR',sans-serif;font-size:7pt;color:#5B6B67;padding:0 15mm;display:flex;justify-content:space-between;">
<span>실무 AI 용어집 · {DATE} 기준</span><span><span class="pageNumber"></span> / <span class="totalPages"></span></span></div>'''


async def render(doc_html, out):
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page()
        await pg.set_content(doc_html, wait_until="load")
        await pg.evaluate("document.fonts.ready")
        await pg.pdf(path=out, format="A4", print_background=True, prefer_css_page_size=True,
                     display_header_footer=True, header_template="<div></div>", footer_template=FOOTER,
                     outline=True, tagged=True)
        await b.close()


def find_pages(path):
    found = {}
    with pdfplumber.open(path) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            # 1pt 표식 글자만 골라 읽어야 같은 높이의 본문 글자와 섞이지 않는다
            tiny = page.filter(lambda o: o.get("object_type") != "char" or o.get("size", 9) < 2)
            txt = "".join(c["text"] for c in sorted(tiny.chars, key=lambda c: (c["x0"] > page.width / 2, round(c["top"]), c["x0"]))).replace(" ", "")
            txt = unicodedata.normalize("NFKC", txt)  # fi·fl·ff 합자를 풀어 id와 맞춘다
            for m in re.finditer(r"§([a-z0-9-]+)§", txt):
                found.setdefault(m.group(1), i)
    return found


if __name__ == "__main__":
    tmp = os.path.join(ROOT, "build", "pass1.pdf"); os.makedirs(os.path.dirname(tmp), exist_ok=True)
    asyncio.run(render(build(), tmp))
    pages = find_pages(tmp)
    missing = [t["id"] for t in TERMS if t["id"] not in pages]
    print("located", len(pages), "missing", missing[:10])
    with pdfplumber.open(tmp) as pdf:
        total = len(pdf.pages)
    out = f"{ROOT}/ai-glossary.pdf"
    asyncio.run(render(build(pages, total), out))
    check = find_pages(out)
    drift = [k for k in pages if check.get(k) != pages[k]]
    print("drift", drift[:10])
    with pdfplumber.open(out) as pdf:
        print("pages", len(pdf.pages))
