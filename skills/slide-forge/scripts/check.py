#!/usr/bin/env python3
"""Rendered quality check for a built Slide Forge deck (Playwright + Chromium).

    python scripts/check.py deck.html                   # report + screenshots in ./qa/
    python scripts/check.py deck.html --out qa --density reading
    python scripts/check.py deck.html --motion 5        # filmstrip of slide 5's animation (mid-frames)
    python scripts/check.py deck.html --only 3,7        # just some slides

Detects, per slide (final state, all build steps revealed):
  ERROR  overflow        content clipped by a container, or past the 1920×1080 stage
  ERROR  overlap         text boxes of two different blocks intersect
  ERROR  tiny-text       text under 20px on the 1920px stage (unreadable when projected)
  ERROR  contrast        text/background contrast under 3:1
  ERROR  broken-image    image failed to load
  ERROR  js-error        console / page errors
  WARN   margin          content crosses the safe margin (80px) without .bleed
  WARN   small-text      text 20–23px (fine for sources/captions only)
  WARN   contrast-aa     contrast under 4.5:1 for body-size text
  WARN   density         too many characters / bullets for the chosen density mode
  WARN   widow           a heading's last line is 1–2 characters (Japanese 泣き別れ)
  WARN   long-headline   headline wraps to more than 3 lines
  ERROR  text-on-image   text over a photo below 3:1 (measured on rendered pixels)
  ERROR  text-over-graphic  text collides with a solid graphic (.solid / --solid:1 / content image)
  WARN   graphic-clipped   a solid graphic runs off the slide
  WARN   low-res         image upscaled >1.3× (soft on a projector)
  WARN   font-fallback   declared web font did not load (system font used)
  ERROR  missing-resource  a local file referenced by the deck failed to load
Outputs: qa/report.md, qa/report.json, qa/slide-XX.png, qa/contact-sheet-N.png
Exit code 1 when any ERROR exists — loop: fix → rebuild → check until clean.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sys.exit("✗ Playwright missing:  pip install playwright && python -m playwright install chromium")

W, H = 1920, 1080
SAFE = 80            # px — minimum distance of content from the stage edge
MIN_ERR, MIN_WARN = 20, 24   # px at 1920 width ≈ 10–12pt on a projected 16:9 screen
DENSITY = {          # visible characters (JA counts 1/char, EN words ≈ 1/6 char) / bullets per slide
    "speaker": {"chars": 140, "bullets": 4},
    "reading": {"chars": 380, "bullets": 7},
}

MEASURE_JS = r"""
(args) => {
  const {SAFE, MIN_ERR, MIN_WARN} = args;
  const out = [];
  const slides = [...document.querySelectorAll('.deck-stage > section.slide')];
  // parse rgb()/rgba()/color(srgb …) → {rgb:[0-255 x3], a}
  const parse = (c) => { const m = c.match(/-?[\d.]+/g); if (!m) return null; let [r, g, b, a = 1] = m.map(Number);
    if (/^color\(srgb/.test(c)) { r *= 255; g *= 255; b *= 255; } return {rgb: [r, g, b], a}; };
  const L = ([r, g, b]) => { const f = (v) => { v /= 255; return v <= .03928 ? v / 12.92 : Math.pow((v + .055) / 1.055, 2.4); }; return .2126*f(r) + .7152*f(g) + .0722*f(b); };
  const lum = (c) => { const p = parse(c); return p ? {L: L(p.rgb), a: p.a, rgb: p.rgb} : null; };
  const bgOf = (el) => { // nearest opaque background colour; null when an image/gradient is in the way
    for (let n = el; n; n = n.parentElement) {
      const cs = getComputedStyle(n);
      if (cs.backgroundImage && cs.backgroundImage !== 'none' && !n.matches('.slide')) return null;
      const p = parse(cs.backgroundColor); if (p && p.a > 0.85) return p.rgb;
      if (n.matches('.slide')) return p ? p.rgb : null;
    } return null; };
  const ratio = (a, b) => (Math.max(a,b)+.05)/(Math.min(a,b)+.05);
  const textNodesOf = (el) => [...el.childNodes].filter(n => n.nodeType === 3 && n.textContent.trim());
  const visible = (el) => { const cs = getComputedStyle(el); return cs.visibility !== 'hidden' && cs.display !== 'none' && +cs.opacity > 0.05; };

  slides.forEach((slide, idx) => {
    const S = slide.getBoundingClientRect();
    const issues = [];
    const add = (level, code, msg, el) => issues.push({level, code, msg, where: el ? (el.className && typeof el.className === 'string' ? el.tagName.toLowerCase() + '.' + el.className.trim().split(/\s+/).join('.') : el.tagName.toLowerCase()) : ''});
    const bleedOK = (el) => !!el.closest('.bg, .bleed, .L-image > img, .L-image > .media, .deck-chrome, .source, .credit');

    // text blocks = block-level owners of text (inline children such as .ch/.mark/strong fold into their block);
    // rects are trimmed to the line-height so tall glyph boxes on adjacent lines don't count as overlap
    const ownerOf = (el) => { for (let n = el; n && n !== slide; n = n.parentElement) { const d = getComputedStyle(n).display; if (!/^(inline|inline-block|contents)$/.test(d) || n.matches('[data-count], .unit')) return n; } return el; };
    const byOwner = new Map();
    slide.querySelectorAll('*').forEach(el => {
      if (el.closest('aside.notes, svg, script, style')) return;
      if (!visible(el)) return;
      const tn = textNodesOf(el); if (!tn.length) return;
      const owner = ownerOf(el); const ocs = getComputedStyle(owner);
      const fs = parseFloat(ocs.fontSize); const lh = ocs.lineHeight === 'normal' ? fs * 1.2 : parseFloat(ocs.lineHeight);
      const r = document.createRange(); const rects = byOwner.get(owner) || [];
      tn.forEach(t => { r.selectNodeContents(t); [...r.getClientRects()].forEach(x => {
        if (x.width <= 1 || x.height <= 1) return;
        const h = Math.min(x.height, lh), cy = x.top + x.height / 2;
        rects.push({left: x.left, right: x.right, top: cy - h / 2, bottom: cy + h / 2}); }); });
      if (rects.length) byOwner.set(owner, rects);
    });
    const blocks = [...byOwner].map(([el, rects]) => ({el, rects}));

    // 1. overflow: clipped containers + stage bounds
    if (slide.scrollHeight > slide.clientHeight + 2 || slide.scrollWidth > slide.clientWidth + 2)
      add('error', 'overflow', `slide content exceeds the stage (${slide.scrollWidth}×${slide.scrollHeight})`, slide);
    slide.querySelectorAll('*').forEach(el => {
      if (el.closest('aside.notes, svg, .deck-chrome') || !visible(el)) return;
      const cs = getComputedStyle(el);
      const clips = /(hidden|clip|auto|scroll)/.test(cs.overflow + cs.overflowX + cs.overflowY);
      if (clips && !el.matches('.slide, .track, .bar .track, .frame, .donut, .code, .thumb, .zoom-view, .ba-slider, [data-anim="mask"] .sf-w, .bento > *') && !el.closest('.bleed, .bg, .zoom-canvas') && (el.scrollHeight > el.clientHeight + 3 || el.scrollWidth > el.clientWidth + 3))
        add('error', 'overflow', `content clipped inside container (${el.scrollWidth}×${el.scrollHeight} > ${el.clientWidth}×${el.clientHeight})`, el);
      if (el.matches('.code') && (el.scrollHeight > el.clientHeight + 3 || el.scrollWidth > el.clientWidth + 3))
        add('error', 'overflow', 'code block is clipped – shorten lines/lines or reduce font-size', el);
    });
    blocks.forEach(({el, rects}) => {
      if (bleedOK(el) || el.closest('.deck-chrome')) return;
      for (const q of rects) {
        if (q.right > S.right + 1 || q.bottom > S.bottom + 1 || q.left < S.left - 1 || q.top < S.top - 1) { add('error', 'overflow', `text outside the stage: "${el.textContent.trim().slice(0, 24)}"`, el); break; }
        if (q.right > S.right - SAFE || q.bottom > S.bottom - SAFE + 20 || q.left < S.left + SAFE || q.top < S.top + SAFE - 20) { add('warn', 'margin', `text inside the ${SAFE}px safe margin: "${el.textContent.trim().slice(0, 24)}"`, el); break; }
      }
    });

    // 2. overlap between different text blocks (ignoring ancestor/descendant pairs)
    for (let i = 0; i < blocks.length; i++) for (let j = i + 1; j < blocks.length; j++) {
      const A = blocks[i], B = blocks[j];
      if (A.el.contains(B.el) || B.el.contains(A.el)) continue;
      const cmp = A.el.closest('.ba-slider');                 // before/after layers are stacked on purpose (one is clipped away)
      if (cmp && cmp.contains(B.el)) continue;
      const pin = A.el.closest('.mk-japan .mk-anchor') || B.el.closest('.mk-japan .mk-anchor');   // map pins sit on top of tiles on purpose
      if (pin && pin.closest('.mk-japan').contains(A.el) && pin.closest('.mk-japan').contains(B.el)) continue;
      let hit = false;
      for (const a of A.rects) { for (const b of B.rects) {
        const ix = Math.min(a.right, b.right) - Math.max(a.left, b.left), iy = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top);
        if (ix > 4 && iy > 4) { hit = true; break; } } if (hit) break; }
      if (hit) add('error', 'overlap', `text overlaps: "${A.el.textContent.trim().slice(0, 18)}" × "${B.el.textContent.trim().slice(0, 18)}"`, A.el);
    }

    // 2b. solid graphics (.solid, [data-solid], --solid:1, content images) must not sit under text or leave the stage
    const isSolid = (el) => el.matches('.solid, [data-solid]') || getComputedStyle(el).getPropertyValue('--solid').trim() === '1'
      || (el.matches('img') && !el.closest('.media-bg, .bg') && !el.matches('.L-image > img'));
    const solids = [...slide.querySelectorAll('*')].filter(el => !el.closest('aside.notes, .deck-chrome') && visible(el) && isSolid(el) && !(el.parentElement && el.parentElement !== slide && isSolid(el.parentElement)));
    solids.forEach(g => {
      const q = g.getBoundingClientRect(); if (q.width < 4 || q.height < 4) return;
      if (q.right > S.right + 2 || q.bottom > S.bottom + 2 || q.left < S.left - 2 || q.top < S.top - 2)
        add('warn', 'graphic-clipped', `graphic extends past the slide edge by ${Math.round(Math.max(q.right - S.right, q.bottom - S.bottom, S.left - q.left, S.top - q.top))}px – move it in or mark it .bleed`, g);
      for (const {el, rects} of blocks) {
        if (g.contains(el) || el.contains(g) || el.closest('.credit')) continue;
        const mroot = g.closest('.mk-app, .mk-sheet, .mk-er, .mk-diagram, .mk-chart');            // a mockup's own text, notes and callouts may sit on it
        if (mroot && mroot.contains(el)) continue;
        const layer = g.closest('.ba-slider, .zoom-canvas');                                         // stacked / zoomed layers
        if (layer && layer.contains(el)) continue;
        if (rects.some(a => Math.min(a.right, q.right) - Math.max(a.left, q.left) > 6 && Math.min(a.bottom, q.bottom) - Math.max(a.top, q.top) > 6)) {
          add('error', 'text-over-graphic', `text "${el.textContent.trim().slice(0, 20)}" is covered by / collides with a graphic`, g); break; }
      }
    });

    // 3. font size + contrast (text over photos is measured from pixels instead – see 'text-on-image')
    const seen = new Set();
    const imgBoxes = [...slide.querySelectorAll('img')].filter(i => !i.closest('aside.notes')).map(i => i.getBoundingClientRect()).filter(q => q.width > 4);
    const onImg = (rects) => rects.some(a => imgBoxes.some(q => Math.min(q.right, a.right) - Math.max(q.left, a.left) > 8 && Math.min(q.bottom, a.bottom) - Math.max(q.top, a.top) > 8));
    blocks.forEach(({el}) => {
      if (el.closest('.deck-chrome')) return;
      const cs = getComputedStyle(el); const fs = parseFloat(cs.fontSize);
      const tag = el.textContent.trim().slice(0, 24);
      if (fs < MIN_ERR && !el.closest('.source, .credit, .zoom-canvas')) add('error', 'tiny-text', `${fs}px text: "${tag}"`, el);
      else if (fs < MIN_WARN && !el.closest('.source, .kicker, .tag, .label, .caption, figcaption, .credit, .credits, .mk-er, .mk-sheet, .mk-device, .mk-w, .mk-chart, .mk-diagram, .zoom-canvas, .sf-3d-label')) add('warn', 'small-text', `${fs}px text: "${tag}"`, el);
      if (cs.color === 'rgba(0, 0, 0, 0)' || cs.webkitTextFillColor === 'rgba(0, 0, 0, 0)') return;
      if (onImg(blocks.find(b => b.el === el).rects)) return;
      const fp = parse(cs.color); const bg = bgOf(el);
      if (!fp || bg == null) return;
      const a = fp.a * (+cs.opacity || 1);
      const mixed = fp.rgb.map((v, k) => v * a + bg[k] * (1 - a));      // semi-transparent text over its background
      const cr = ratio(L(mixed), L(bg)); const large = fs >= 36 || (fs >= 28 && +cs.fontWeight >= 700);
      const key = cs.color + '|' + bg.join(',');
      if (seen.has(key)) return; seen.add(key);
      if (cr < 3) add('error', 'contrast', `contrast ${cr.toFixed(2)}:1 for "${tag}"`, el);
      else if (cr < 4.5 && !large) add('warn', 'contrast-aa', `contrast ${cr.toFixed(2)}:1 for body-size text "${tag}"`, el);
    });

    // 4. headings: lines, widows
    slide.querySelectorAll('h1, h2, h3, .hero, .headline, .statement, .points > li, .lede, .card p, .quote').forEach(h => {
      if (!visible(h) || h.closest('aside.notes')) return;
      const r = document.createRange(); r.selectNodeContents(h);
      const lines = []; [...r.getClientRects()].forEach(q => { if (q.width < 2) return; const l = lines.find(L => Math.abs(L.top - q.top) < q.height * .5); l ? (l.right = Math.max(l.right, q.right), l.left = Math.min(l.left, q.left)) : lines.push({top: q.top, left: q.left, right: q.right, h: q.height}); });
      if (lines.length > 3 && h.matches('h1, h2, .hero, .headline')) add('warn', 'long-headline', `headline wraps to ${lines.length} lines – shorten it or split the idea`, h);
      if (lines.length >= 2) {
        const last = lines.sort((a, b) => a.top - b.top).at(-1); const em = parseFloat(getComputedStyle(h).fontSize);
        if ((last.right - last.left) < em * 2.2) add('warn', 'widow', `line ends with an orphaned 1–2 character line: "${h.textContent.trim().slice(-6)}"`, h);
      }
    });

    // 5. images: broken / upscaled (blurry when projected)
    const imgRects = [];
    slide.querySelectorAll('img').forEach(img => {
      if (img.closest('aside.notes')) return;
      if (!img.complete || img.naturalWidth === 0) { add('error', 'broken-image', `image failed to load: ${img.getAttribute('src')?.slice(0, 60)}`, img); return; }
      const r = img.getBoundingClientRect(); if (r.width < 4 || r.height < 4) return;
      imgRects.push(r);
      const fit = getComputedStyle(img).objectFit;
      const up = fit === 'cover' ? Math.max(r.width / img.naturalWidth, r.height / img.naturalHeight) : Math.min(r.width / img.naturalWidth, r.height / img.naturalHeight);
      if (up > 1.3 && !img.src.endsWith('.svg') && !img.src.startsWith('data:image/svg')) add('warn', 'low-res', `image shown at ${up.toFixed(1)}× its pixel size (${img.naturalWidth}px wide) – looks soft when projected; use a larger source or a smaller frame`, img);
    });
    // text sitting on a photo: formula contrast is meaningless → measured from pixels later (python)
    const overImage = [];
    blocks.forEach(({el, rects}) => {
      if (el.closest('.credit, .deck-chrome')) return;
      const box = rects.reduce((a, q) => ({l: Math.min(a.l, q.left), t: Math.min(a.t, q.top), r: Math.max(a.r, q.right), b: Math.max(a.b, q.bottom)}), {l: 1e9, t: 1e9, r: -1e9, b: -1e9});
      const hit = imgRects.some(q => Math.min(q.right, box.r) - Math.max(q.left, box.l) > 8 && Math.min(q.bottom, box.b) - Math.max(q.top, box.t) > 8);
      if (!hit) return;
      el.__overImage = true;
      const p = parse(getComputedStyle(el).color);
      overImage.push({text: el.textContent.trim().slice(0, 24), rgb: p ? p.rgb : [0, 0, 0], fs: parseFloat(getComputedStyle(el).fontSize),
                      box: {x: box.l - S.left, y: box.t - S.top, w: box.r - box.l, h: box.b - box.t}});
    });

    // 6. density
    const clone = slide.cloneNode(true); clone.querySelectorAll('aside.notes, .deck-chrome, .source, .kicker, pre, code, script, style, [aria-hidden="true"], [data-density-skip]').forEach(n => n.remove());
    const txt = clone.textContent.replace(/\s+/g, ' ').trim();
    const cjk = (txt.match(/[　-ヿ㐀-鿿＀-￯]/g) || []).length;
    const latin = txt.replace(/[　-ヿ㐀-鿿＀-￯]/g, '').replace(/\s+/g, ' ').trim().length;
    const chars = cjk + Math.round(latin / 2.2);
    const bullets = Math.max(0, ...[...slide.querySelectorAll('ul, ol')].filter(l => !l.closest('aside.notes')).map(l => l.children.length));
    const title = (slide.querySelector('h1, h2, .hero, .headline, .statement')?.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 140);
    out.push({index: idx + 1, title, layout: [...slide.classList].filter(c => c.startsWith('L-')).join(' '),
      chars, bullets, steps: slide.querySelectorAll('[data-step]').length, anims: slide.querySelectorAll('[data-anim]').length,
      hasNotes: !!slide.querySelector('aside.notes'), issues, overImage,
      rect: {x: S.x + window.scrollX, y: S.y + window.scrollY, w: S.width, h: S.height}});
  });
  return out;
}
"""

FONT_JS = r"""
() => { const fams = new Set(); document.fonts.forEach(f => fams.add(f.family.replace(/["']/g, '') + '|' + f.status));
  const used = new Set(); document.querySelectorAll('.slide *').forEach(el => { const f = getComputedStyle(el).fontFamily.split(',')[0].replace(/["']/g, '').trim(); used.add(f); });
  return {faces: [...fams], used: [...used]}; }
"""


def _lum(rgb):
    f = lambda v: (v / 255) / 12.92 if v / 255 <= .03928 else (((v / 255) + .055) / 1.055) ** 2.4  # noqa: E731
    return .2126 * f(rgb[0]) + .7152 * f(rgb[1]) + .0722 * f(rgb[2])


def text_on_image(png: bytes, blocks: list, scale: float) -> list:
    """Contrast of text over photos, measured on rendered pixels.
    Glyph pixels (close to the text colour) are ignored; the background is judged at its
    worst common point (the 90th percentile nearest the text luminance)."""
    try:
        from PIL import Image
    except ImportError:
        return []
    import io
    im = Image.open(io.BytesIO(png)).convert("RGB")
    out = []
    for b in blocks:
        bx = b["box"]
        pad = 6
        box = [int(max(0, (bx["x"] - pad) * scale)), int(max(0, (bx["y"] - pad) * scale)),
               int(min(im.width, (bx["x"] + bx["w"] + pad) * scale)), int(min(im.height, (bx["y"] + bx["h"] + pad) * scale))]
        if box[2] - box[0] < 3 or box[3] - box[1] < 3:
            continue
        region = im.crop(box)
        lt = _lum(b["rgb"])
        # glyph mask: pixels near the text colour, dilated so anti-aliased edges are excluded too
        from PIL import ImageFilter
        lum_img = region.convert("L")
        tl = round(255 * (lt ** (1 / 2.2)))           # approx. text brightness in gamma space
        mask = lum_img.point(lambda v: 255 if abs(v - tl) < 70 else 0).filter(ImageFilter.MaxFilter(5))
        px, mk = region.load(), mask.load()
        step = max(1, (region.width * region.height) // 6000)
        bg = []
        for i in range(0, region.width * region.height, step):
            x, y = i % region.width, i // region.width
            if not mk[x, y]:
                bg.append(_lum(px[x, y]))
        bg.sort()
        covered = sum(1 for v in (mask.get_flattened_data() if hasattr(mask, "get_flattened_data") else mask.getdata()) if v) / max(1, mask.width * mask.height) if hasattr(mask, "getdata") else 0
        if covered > 0.8:   # "glyph-coloured" pixels everywhere → background ≈ text colour
            out.append({"level": "error", "code": "text-on-image", "msg": f"text colour is almost the same as the photo behind it: \"{b['text']}\" – add a scrim or darken the photo", "where": ""})
            continue
        if len(bg) < 30:
            continue
        worst = bg[int(len(bg) * 0.9)] if lt > 0.5 else bg[int(len(bg) * 0.1)]   # bg side closest to the text colour
        cr = (max(lt, worst) + .05) / (min(lt, worst) + .05)
        large = b["fs"] >= 36
        if cr < 3:
            out.append({"level": "error", "code": "text-on-image", "msg": f"text over photo has {cr:.1f}:1 contrast at its worst point: \"{b['text']}\" – add/strengthen the scrim (.media-bg), darken the photo (assets.py --treat darken) or move the text", "where": ""})
        elif cr < 4.5 and not large:
            out.append({"level": "warn", "code": "text-on-image", "msg": f"text over photo {cr:.1f}:1 for body-size text: \"{b['text']}\"", "where": ""})
    return out


def contact_sheets(pngs: list[Path], out: Path, cols=3, per=12) -> list[Path]:
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("  (Pillow not installed – skipping contact sheet: pip install pillow)")
        return []
    tw, th, pad, lab = 640, 360, 24, 36
    sheets = []
    for s in range(0, len(pngs), per):
        chunk = pngs[s:s + per]
        rows = math.ceil(len(chunk) / cols)
        sheet = Image.new("RGB", (cols * (tw + pad) + pad, rows * (th + pad + lab) + pad), (24, 24, 28))
        d = ImageDraw.Draw(sheet)
        try:
            font = ImageFont.truetype("DejaVuSans-Bold.ttf", 22)
        except OSError:
            font = ImageFont.load_default()
        for k, p in enumerate(chunk):
            im = Image.open(p).convert("RGB").resize((tw, th), Image.LANCZOS)
            x, y = pad + (k % cols) * (tw + pad), pad + (k // cols) * (th + pad + lab)
            sheet.paste(im, (x, y + lab))
            d.text((x, y + 6), p.stem.replace("slide-", "#"), fill=(230, 230, 230), font=font)
        path = out / f"contact-sheet-{s // per + 1}.png"
        sheet.save(path)
        sheets.append(path)
    return sheets


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("deck", type=Path)
    ap.add_argument("--out", type=Path, default=Path("qa"))
    ap.add_argument("--density", choices=["speaker", "reading"], help="default: deck-config density or speaker")
    ap.add_argument("--only", help="comma-separated slide numbers")
    ap.add_argument("--motion", type=int, help="also capture an animation filmstrip for this slide number")
    ap.add_argument("--no-shots", action="store_true", help="skip screenshots (faster)")
    ap.add_argument("--scale", type=float, default=0.5, help="screenshot scale (0.5 → 960×540 per slide)")
    a = ap.parse_args()
    if not a.deck.is_file():
        sys.exit(f"✗ {a.deck} not found")
    a.out.mkdir(parents=True, exist_ok=True)
    only = {int(x) for x in a.only.split(",")} if a.only else None
    url = a.deck.resolve().as_uri()

    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": W, "height": H}, device_scale_factor=a.scale)
        page = ctx.new_page()
        errors: list[str] = []
        page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
        page.on("console", lambda m: errors.append(f"console.{m.type}: {m.text}") if m.type == "error" and "Failed to load resource" not in m.text else None)
        failed_req: list[str] = []
        page.on("requestfailed", lambda r: failed_req.append(r.url))
        page.goto(url + "?export", wait_until="load")
        page.wait_for_function("window.deck && document.documentElement.classList.contains('sf-ready')", timeout=30000)
        page.wait_for_timeout(400)
        density = a.density or page.evaluate("() => (window.DECK_CONFIG||{}).density") or "speaker"
        # deck-config density isn't passed to the runtime by default; read it from a meta if present
        limits = DENSITY.get(density, DENSITY["speaker"])
        data = page.evaluate(MEASURE_JS, {"SAFE": SAFE, "MIN_ERR": MIN_ERR, "MIN_WARN": MIN_WARN})
        fonts = page.evaluate(FONT_JS)

        # collapse repeats: at most 3 issues per (slide, code); the rest summarised
        for s in data:
            kept, count = [], {}
            for i in s["issues"]:
                count[i["code"]] = count.get(i["code"], 0) + 1
                if count[i["code"]] <= 3:
                    kept.append(i)
            for code, n in count.items():
                if n > 3:
                    lvl = next(i["level"] for i in s["issues"] if i["code"] == code)
                    kept.append({"level": lvl, "code": code, "msg": f"…and {n - 3} more {code} issue(s) on this slide", "where": ""})
            s["issues"] = kept
        errors[:] = list(dict.fromkeys(errors))

        shots = []
        for s in data:
            if only and s["index"] not in only:
                continue
            if "L-credits" in s["layout"]:
                pass
            elif s["chars"] > limits["chars"]:
                s["issues"].append({"level": "warn", "code": "density", "msg": f"{s['chars']} chars (> {limits['chars']} for {density} mode) – cut words or split the slide", "where": ""})
            if s["bullets"] > limits["bullets"] and "L-credits" not in s["layout"]:
                s["issues"].append({"level": "warn", "code": "density", "msg": f"{s['bullets']} bullets in one list (> {limits['bullets']} for {density} mode)", "where": ""})
            r = s["rect"]
            clip = {"x": r["x"], "y": r["y"], "width": r["w"], "height": r["h"]}
            png = None
            if not a.no_shots:
                path = a.out / f"slide-{s['index']:02d}.png"
                page.screenshot(path=str(path), clip=clip, full_page=True)
                shots.append(path); png = path.read_bytes()
            if s.get("overImage"):
                png = png or page.screenshot(clip=clip, full_page=True)
                for iss in text_on_image(png, s["overImage"], a.scale):
                    s["issues"].append(iss)

        # font fallback detection
        failed = sorted({f.split("|")[0] for f in fonts["faces"] if f.endswith("|error")})
        loaded = {f.split("|")[0] for f in fonts["faces"] if f.endswith("|loaded")}
        declared = {f.split("|")[0] for f in fonts["faces"]}
        missing = sorted({u for u in fonts["used"] if u and u not in declared and u not in loaded and u.lower() not in ("monospace", "serif", "sans-serif", "system-ui", "ui-monospace")})
        global_issues = []
        if failed:
            global_issues.append({"level": "warn", "code": "font-fallback", "msg": f"web fonts failed to load: {', '.join(failed)}"})
        if missing and not loaded:
            global_issues.append({"level": "warn", "code": "font-fallback", "msg": "no web fonts loaded (offline? use build --fonts embed). Rendering used system fonts"})
        font_fail = [u for u in failed_req if "fonts.g" in u]
        other_fail = [u for u in failed_req if "fonts.g" not in u and not u.startswith("data:")]
        if font_fail:
            global_issues.append({"level": "warn", "code": "font-fallback", "msg": f"could not reach Google Fonts ({len(font_fail)} request(s)) – offline/blocked network. Use build --fonts embed for offline decks"})
        for u in dict.fromkeys(other_fail):
            global_issues.append({"level": "error", "code": "missing-resource", "msg": f"failed to load {u[:120]}"})
        for e in errors:
            global_issues.append({"level": "error", "code": "js-error", "msg": e})

        # motion filmstrip: real show mode, capture frames after entering the slide
        if a.motion:
            mp = ctx.new_page()
            mp.goto(url + f"#/{max(1, a.motion - 1)}", wait_until="load")
            mp.wait_for_function("document.documentElement.classList.contains('sf-ready')")
            mp.wait_for_timeout(300)
            mp.evaluate(f"() => deck.go({a.motion - 1}, 0, {{dir: 1}})")
            frames = []
            t0 = 0
            for t in (0, 120, 300, 550, 900, 1500, 2600):
                mp.wait_for_timeout(t - t0); t0 = t
                fp = a.out / f"motion-{a.motion:02d}-{t:04d}ms.png"
                mp.screenshot(path=str(fp)); frames.append(fp)
            steps = mp.evaluate("() => deck.steps()")
            for k in range(steps):
                mp.keyboard.press("ArrowRight"); mp.wait_for_timeout(900)
                fp = a.out / f"motion-{a.motion:02d}-step{k + 1}.png"
                mp.screenshot(path=str(fp)); frames.append(fp)
            print(f"  motion filmstrip: {len(frames)} frames → {a.out}/motion-{a.motion:02d}-*.png")
            if frames:
                contact_sheets(frames, a.out, cols=4, per=16)[0].rename(a.out / f"motion-{a.motion:02d}-strip.png")
        browser.close()

    sheets = contact_sheets(shots, a.out) if shots else []
    n_err = sum(1 for s in data for i in s["issues"] if i["level"] == "error") + sum(1 for i in global_issues if i["level"] == "error")
    n_warn = sum(1 for s in data for i in s["issues"] if i["level"] == "warn") + sum(1 for i in global_issues if i["level"] == "warn")

    # report
    lines = [f"# QA report — {a.deck.name}", "",
             f"**{len(data)} slides · {n_err} errors · {n_warn} warnings** · density mode: {density}", ""]
    for i in global_issues:
        lines.append(f"- {'✗' if i['level'] == 'error' else '⚠'} **{i['code']}** {i['msg']}")
    lines += ["", "| # | layout | title | chars | bullets | steps | notes | issues |", "|---|---|---|---|---|---|---|---|"]
    for s in data:
        if only and s["index"] not in only:
            continue
        iss = "; ".join(f"{'✗' if i['level'] == 'error' else '⚠'} {i['code']}" for i in s["issues"]) or "✓"
        lines.append(f"| {s['index']} | {s['layout']} | {s['title'][:34]} | {s['chars']} | {s['bullets']} | {s['steps']} | {'✓' if s['hasNotes'] else '—'} | {iss} |")
    lines += ["", "## Details", ""]
    for s in data:
        if s["issues"] and (not only or s["index"] in only):
            lines.append(f"### Slide {s['index']} — {s['title'][:50]}")
            lines += [f"- {'✗' if i['level'] == 'error' else '⚠'} `{i['code']}` {i['msg']}" + (f"  ({i['where'][:60]})" if i.get("where") else "") for i in s["issues"]]
            lines.append("")
    if sheets:
        lines += ["## Contact sheets", *[f"- {p.name}" for p in sheets]]
    (a.out / "report.md").write_text("\n".join(lines), encoding="utf-8")
    (a.out / "report.json").write_text(json.dumps({"slides": data, "global": global_issues, "errors": n_err, "warnings": n_warn}, ensure_ascii=False, indent=1), encoding="utf-8")

    # console summary (compact, agent-friendly)
    print(f"{'✗' if n_err else '✓'} {a.deck.name}: {len(data)} slides, {n_err} errors, {n_warn} warnings  → {a.out}/report.md")
    for i in global_issues:
        print(f"  {'✗' if i['level'] == 'error' else '⚠'} {i['code']}: {i['msg']}")
    for s in data:
        for i in s["issues"]:
            if only and s["index"] not in only:
                continue
            print(f"  {'✗' if i['level'] == 'error' else '⚠'} slide {s['index']:>2} {i['code']}: {i['msg']}")
    if sheets:
        print(f"  contact sheet(s): {', '.join(str(p) for p in sheets)}  ← LOOK at these before delivering")
    sys.exit(1 if n_err else 0)


if __name__ == "__main__":
    main()
