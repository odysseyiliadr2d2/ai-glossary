"""링크 미리보기용 대표 이미지(og-image.png, 1200×630)를 학습 카드형 디자인으로 만든다.
숫자(문서·분야·주제·논문)는 data/에서 읽으므로 업데이트 때마다 다시 만들면 최신 값이 들어간다."""
import json, os, asyncio
from playwright.async_api import async_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
terms = [t for t in json.load(open(f"{ROOT}/data/terms.json", encoding="utf-8")) if t["status"] == "active"]
tree = json.load(open(f"{ROOT}/data/tree.json", encoding="utf-8"))
papers = {p["url"] for t in terms for p in t.get("papers", [])}
topics = sum(len(c["topics"]) for c in tree)
CAT_COLORS = ["#dbe7ff", "#ece0ff", "#cdf1ea", "#fff0b8", "#ffdcd6", "#d4f5dd", "#dfe1ff", "#ffdcef", "#e2e6ee", "#ffe0e4", "#ffe9c7"]
chips = "".join(f'<span style="background:{CAT_COLORS[i % len(CAT_COLORS)]}">{c["ko"]}</span>' for i, c in enumerate(tree[:6]))
if len(tree) > 6:
    chips += f'<span style="background:#ffffff">외 {len(tree) - 6}개 분야</span>'

HTML = f"""<!doctype html><html lang="ko"><head><meta charset="utf-8"><style>
* {{ box-sizing: border-box; margin: 0; }}
body {{ width: 1200px; height: 630px; background: #f4f6fb; font-family: "Noto Sans CJK KR", sans-serif; color: #1b1f3b; padding: 40px; }}
.hero {{ height: 100%; background: #3d35b8; border-radius: 36px; padding: 56px 60px; color: #fff; display: flex; flex-direction: column; }}
.logo {{ display: flex; align-items: center; gap: 14px; font-size: 26px; font-weight: 700; }}
.logo i {{ width: 52px; height: 52px; border-radius: 14px; background: #ffd84d; color: #1b1f3b; display: grid; place-items: center; font-style: normal; font-weight: 900; font-size: 22px; }}
h1 {{ font-size: 64px; font-weight: 900; line-height: 1.15; letter-spacing: -1.5px; margin-top: 34px; }}
p {{ font-size: 26px; color: #e3e1ff; margin-top: 16px; }}
.row {{ margin-top: auto; display: flex; justify-content: space-between; align-items: flex-end; gap: 24px; }}
.stats {{ display: flex; gap: 14px; }}
.stats div {{ background: rgba(255,255,255,.15); border-radius: 22px; padding: 16px 22px; }}
.stats b {{ display: block; font-size: 40px; font-weight: 900; line-height: 1; }}
.stats span {{ font-size: 18px; color: #e3e1ff; }}
.chips {{ display: flex; flex-wrap: wrap; gap: 8px; max-width: 470px; justify-content: flex-end; }}
.chips span {{ color: #1b1f3b; font-size: 16px; font-weight: 700; padding: 6px 14px; border-radius: 999px; }}
</style></head><body><div class="hero">
<div class="logo"><i>AI</i>실무 AI 용어집</div>
<h1>오늘은 어떤 AI 용어가<br>궁금한가요?</h1>
<p>실무자와 개발자를 위한 AI 용어 위키 · 입문과 심화 두 수준으로</p>
<div class="row">
  <div class="stats"><div><b>{len(terms)}</b><span>문서</span></div><div><b>{topics}</b><span>주제</span></div><div><b>{len(papers)}</b><span>논문</span></div></div>
  <div class="chips">{chips}</div>
</div></div></body></html>"""


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={"width": 1200, "height": 630})
        await pg.set_content(HTML, wait_until="load")
        await pg.evaluate("document.fonts.ready")
        await pg.screenshot(path=f"{ROOT}/og-image.png")
        await b.close()

asyncio.run(main())
print("og-image.png", len(terms), topics, len(papers))
