#!/usr/bin/env python3
"""Theme catalogue + visual previews ("show, don't tell" style picking).

    python scripts/themes.py list
    python scripts/themes.py preview --title "来期の開発方針" --subtitle "技術部 全体会議" \
        --points "品質を仕組みで守る,AIで設計を速くする,チームで学び続ける" \
        --themes swiss,blueprint,signal --out previews/

`preview` writes one mini deck per theme (cover + one content slide, built from the user's
own words — never placeholder or process labels) and a labelled gallery.png to show the user.
Custom theme files (path to .css) are accepted in --themes too.
"""
from __future__ import annotations

import argparse
import html
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
THEMES = HERE.parent / "assets" / "themes"
sys.path.insert(0, str(HERE))


def meta(path: Path) -> dict:
    head = path.read_text(encoding="utf-8").split("*/", 1)[0]
    d = {k: v.strip() for k, v in re.findall(r"@(theme|name|scheme|mood|best)\s+([^\n]+)", head)}
    d["fonts"] = ", ".join(m.split("|")[0].strip() for m in re.findall(r"@font\s+([^\n]+)", head))
    d["path"] = str(path)
    return d


def cmd_list():
    for p in sorted(THEMES.glob("*.css")):
        m = meta(p)
        print(f"{m.get('theme', p.stem):10} {m.get('scheme', ''):5}  {m.get('name', '')}\n"
              f"{'':17}mood: {m.get('mood', '')}\n{'':17}best: {m.get('best', '')}\n{'':17}fonts: {m['fonts']}\n")


def cmd_preview(a):
    import build as B
    from check import contact_sheets
    from playwright.sync_api import sync_playwright

    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    names = [t.strip() for t in a.themes.split(",")] if a.themes else [p.stem for p in sorted(THEMES.glob("*.css"))]
    pts = [p.strip() for p in (a.points or "").split(",") if p.strip()][:3]
    e = html.escape
    content = ""
    if pts:
        content = f"""
<section class="slide L-bullets">
  <div class="head"><div class="kicker" data-anim="fade">{e(a.kicker or 'Overview')}</div>
  <h2 class="headline" data-anim="up">{e(a.headline or pts[0])}</h2></div>
  <div class="body"><ol class="points numbered big" data-stagger="up">{''.join(f'<li>{e(x)}</li>' for x in pts)}</ol></div>
</section>"""
    shots = []
    with sync_playwright() as p:
        br = p.chromium.launch()
        page = br.new_page(viewport={"width": 1920, "height": 1080}, device_scale_factor=0.5)
        for name in names:
            src = out / f"{Path(name).stem}.src.html"
            src.write_text(f"""<script type="application/json" id="deck-config">{{"title": "{e(a.title)}", "theme": "{name}", "lang": "{a.lang}", "footer": "{e(a.footer or '')}", "density": "speaker"}}</script>
<section class="slide L-title" data-chrome="off">
  <div class="kicker" data-anim="fade">{e(a.kicker or a.subtitle or '')}</div>
  <h1 class="hero" data-anim="up">{e(a.title)}</h1>
  {f'<p class="lede" data-anim="up">{e(a.subtitle)}</p>' if a.subtitle else ''}
</section>{content}
""", encoding="utf-8")
            built, errs = B.build(src, out / f"{Path(name).stem}.html", None, a.fonts, True, quiet=True)
            page.goto(built.resolve().as_uri() + "?export&nochrome")
            page.wait_for_function("document.documentElement.classList.contains('sf-ready')")
            page.wait_for_timeout(300)
            rects = page.evaluate("() => [...document.querySelectorAll('.deck-stage > section.slide')].map(s => { const r = s.getBoundingClientRect(); return {x: r.x + scrollX, y: r.y + scrollY, width: r.width, height: r.height}; })")
            for k, r in enumerate(rects):
                shot = out / f"slide-{Path(name).stem}-{k + 1}.png"
                page.screenshot(path=str(shot), clip=r, full_page=True)
                shots.append(shot)
                if k == 0:   # keep each theme's cover as its own image (e.g. for a "same text, N themes" slide)
                    (out / f"{Path(name).stem}.png").write_bytes(shot.read_bytes())
            src.unlink()
        br.close()
    sheets = contact_sheets(shots, out, cols=2 if pts else 3, per=len(shots))
    if sheets:
        g = out / "gallery.png"; sheets[0].rename(g)
        print(f"✓ gallery {g}  (themes: {', '.join(Path(n).stem for n in names)})")
    for s in shots:
        s.unlink()
    print(f"  previews: {', '.join(str(out / (Path(n).stem + '.html')) for n in names)}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    pv = sub.add_parser("preview")
    pv.add_argument("--title", required=True)
    pv.add_argument("--subtitle", default="")
    pv.add_argument("--kicker", default="")
    pv.add_argument("--headline", default="")
    pv.add_argument("--points", default="", help="up to 3 comma-separated points for the content slide")
    pv.add_argument("--footer", default="")
    pv.add_argument("--themes", default="", help="comma list of theme names / css paths (default: all)")
    pv.add_argument("--lang", default="ja")
    pv.add_argument("--fonts", default="link", choices=["link", "embed", "none"])
    pv.add_argument("--out", default="previews")
    a = ap.parse_args()
    cmd_list() if a.cmd == "list" else cmd_preview(a)


if __name__ == "__main__":
    main()
