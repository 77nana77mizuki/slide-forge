#!/usr/bin/env python3
"""Export a built deck to PDF (vector, selectable text) and/or PNG images.

    python scripts/export.py deck.html                    # → deck.pdf
    python scripts/export.py deck.html --png out_dir      # one PNG per slide (1920×1080)
    python scripts/export.py deck.html --pdf talk.pdf --png shots --scale 1

The PDF uses the deck's export mode (all build steps revealed, animations at their final state).
Default is vector output — text stays selectable/searchable. Decks with heavy photo effects
(blend modes, filters, full-bleed photos on every slide) can come out very large because Chrome
rasterises those layers per page; then use --raster (JPEG pages, typically 5–10× smaller,
text not selectable):   python scripts/export.py deck.html --raster [--quality 82]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sys.exit("✗ Playwright missing:  pip install playwright && python -m playwright install chromium")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("deck", type=Path)
    ap.add_argument("--pdf", type=Path, help="PDF path (default: next to the deck, unless only --png is given)")
    ap.add_argument("--png", type=Path, help="directory for per-slide PNGs")
    ap.add_argument("--scale", type=float, default=1.0, help="PNG pixel ratio (1 → 1920×1080, 2 → 3840×2160)")
    ap.add_argument("--no-chrome", action="store_true", help="omit page numbers / footer")
    ap.add_argument("--raster", action="store_true", help="PDF from JPEG screenshots (small file, text not selectable)")
    ap.add_argument("--quality", type=int, default=82, help="JPEG quality for --raster (82 ≈ visually lossless on a projector)")
    a = ap.parse_args()
    if not a.deck.is_file():
        sys.exit(f"✗ {a.deck} not found")
    pdf = a.pdf or (None if a.png else a.deck.with_suffix(".pdf"))
    url = a.deck.resolve().as_uri() + "?export" + ("&nochrome" if a.no_chrome else "")

    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(viewport={"width": 1920, "height": 1080}, device_scale_factor=a.scale)
        page = ctx.new_page()
        page.goto(url, wait_until="load")
        page.wait_for_function("document.documentElement.classList.contains('sf-ready')", timeout=30000)
        page.wait_for_timeout(500)
        n = page.evaluate("() => document.querySelectorAll('.deck-stage > section.slide').length")
        rects = page.evaluate("() => [...document.querySelectorAll('.deck-stage > section.slide')].map(s => { const r = s.getBoundingClientRect(); return {x: r.x + scrollX, y: r.y + scrollY, width: r.width, height: r.height}; })")
        if pdf and a.raster:
            from PIL import Image
            import io
            pages = [Image.open(io.BytesIO(page.screenshot(clip=r, full_page=True))).convert("RGB") for r in rects]
            buf = []
            for im in pages:   # re-encode as JPEG so the PDF embeds DCT streams, not raw pixels
                jb = io.BytesIO(); im.save(jb, "JPEG", quality=a.quality, optimize=True, progressive=True); buf.append(Image.open(jb))
            buf[0].save(pdf, "PDF", save_all=True, append_images=buf[1:], resolution=72 * a.scale)
            print(f"✓ PDF  {pdf}  ({len(buf)} pages, raster, {pdf.stat().st_size / 1024 / 1024:.1f} MB)")
            pdf = None
        if pdf:
            page.emulate_media(media="print")
            page.pdf(path=str(pdf), width="1920px", height="1080px", print_background=True,
                     margin={"top": "0", "right": "0", "bottom": "0", "left": "0"}, prefer_css_page_size=True)
            mb = pdf.stat().st_size / 1024 / 1024
            print(f"✓ PDF  {pdf}  ({n} pages, {mb:.1f} MB)")
            if mb > 15:
                print(f"  ⚠ {mb:.0f} MB is too big for email/chat – photo effects were rasterised per page. Try: export.py {a.deck} --raster")
            page.emulate_media(media="screen")
        if a.png:
            a.png.mkdir(parents=True, exist_ok=True)
            for i, r in enumerate(rects, 1):
                page.screenshot(path=str(a.png / f"slide-{i:02d}.png"), clip=r, full_page=True)
            print(f"✓ PNG  {a.png}/slide-01..{len(rects):02d}.png")
        b.close()


if __name__ == "__main__":
    main()
