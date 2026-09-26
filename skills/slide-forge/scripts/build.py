#!/usr/bin/env python3
"""Build a Slide Forge deck: source HTML (sections only) → one self-contained HTML file.

    python scripts/build.py deck.src.html                      # → deck.html next to the source
    python scripts/build.py deck.src.html -o dist/talk.html --theme signal
    python scripts/build.py deck.src.html --fonts embed        # offline: embed used glyph subsets
    python scripts/build.py deck.src.html --watch              # rebuild on save

Source format (see assets/examples/sample.src.html):
    <script type="application/json" id="deck-config">{ "title": "…", "theme": "washi", … }</script>
    <style> /* optional deck-specific CSS */ </style>
    <section class="slide L-title"> … </section>
    …

The build also runs a fast STATIC LINT (structure, animation names, notes, images).
Rendered checks (overflow, overlap, contrast, font size) live in scripts/check.py.
"""
from __future__ import annotations

import argparse
import base64
import html
import json
import mimetypes
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent
RUNTIME = SKILL / "assets" / "runtime"
THEMES = SKILL / "assets" / "themes"
sys.path.insert(0, str(HERE))
import fonts as F  # noqa: E402
import assets as A  # noqa: E402
import mock as MK  # noqa: E402

LAYOUTS = {"L-credits", "L-title", "L-section", "L-statement", "L-bullets", "L-split", "L-cards", "L-stats", "L-compare",
           "L-quote", "L-image", "L-closing", "L-chart", "L-timeline", "L-flow", "L-code", "L-table", "L-agenda", "L-free"}
ANIMS = {"up", "down", "from-left", "from-right", "fade", "scale", "zoom", "pop", "blur", "wipe", "wipe-up",
         "draw", "mark", "chars"}
TRANSITIONS = {"fade", "slide", "rise", "zoom", "wipe", "morph", "none"}
MAX_INLINE_IMAGE = 8 * 1024 * 1024   # bytes; bigger files stay as links (keeps the HTML openable)
NO_HEADLINE_OK = {"L-credits", "L-title", "L-image", "L-quote", "L-statement", "L-section", "L-closing", "L-free"}


def theme_path(name: str, src_dir: Path) -> Path:
    for cand in (src_dir / name, src_dir / f"{name}.css", THEMES / f"{name}.css"):
        if cand.is_file():
            return cand
    avail = ", ".join(sorted(p.stem for p in THEMES.glob("*.css")))
    sys.exit(f"✗ theme '{name}' not found. Built-in themes: {avail} (or pass a path to a .css file)")


def split_source(src: str):
    m = re.search(r'<script[^>]*id=["\']deck-config["\'][^>]*>(.*?)</script>', src, re.S)
    if not m:
        sys.exit('✗ missing <script type="application/json" id="deck-config">{…}</script> at the top of the source')
    try:
        cfg = json.loads(m.group(1))
    except json.JSONDecodeError as e:
        sys.exit(f"✗ deck-config is not valid JSON: {e}")
    rest = src[:m.start()] + src[m.end():]
    styles = re.findall(r"<style[^>]*>(.*?)</style>", rest, re.S)
    rest = re.sub(r"<style[^>]*>.*?</style>", "", rest, flags=re.S)
    heads = re.findall(r"<(?:link|meta)[^>]*>", rest.split("<section", 1)[0])
    body = rest[rest.find("<section"):] if "<section" in rest else ""
    # <script> blocks written before the first slide would otherwise be dropped: keep them (moved after the slides)
    pre_scripts = re.findall(r"<script\b.*?</script>", rest.split("<section", 1)[0], re.S)
    if pre_scripts:
        body = body + "\n" + "\n".join(pre_scripts)
    body = re.sub(r"<!--(?!\s*notes).*?-->", "", body, flags=re.S).strip()
    return cfg, "\n".join(styles), heads, body


def visible_text(body: str) -> str:
    t = re.sub(r"<aside class=\"notes\">.*?</aside>", " ", body, flags=re.S)
    t = re.sub(r"<script.*?</script>", " ", t, flags=re.S)
    return html.unescape(re.sub(r"<[^>]+>", " ", t))


def _data_uri(url: str, src_dir: Path, warn) -> str | None:
    """Local file → data: URI (None = leave the reference as it is)."""
    if re.match(r"(data:|https?:|//)", url):
        return None
    p = (src_dir / url).resolve()
    if not p.is_file():
        warn(f"image not found: {url}")
        return None
    if p.stat().st_size > MAX_INLINE_IMAGE:
        warn(f"image {url} is {p.stat().st_size // 1024} KB – left as a relative link (ship it next to the HTML)")
        return None
    mime = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
    return f"data:{mime};base64,{base64.b64encode(p.read_bytes()).decode()}"


def inline_css_urls(text: str, src_dir: Path, warn) -> str:
    """url(img.png) in style attributes or <style> CSS → data URI."""
    def css_url(m):
        uri = _data_uri(m.group(2), src_dir, warn)
        return f"url({uri})" if uri else m.group(0)   # unquoted: data URIs have no quotes/parens, and quotes would break style="…"
    return re.sub(r"url\((['\"]?)(?!data:|https?:)([^)'\"]+)\1\)", css_url, text)


def inline_images(body: str, src_dir: Path, warn) -> str:
    def repl(m):
        attr, q, url = m.group(1), m.group(2), m.group(3)
        uri = _data_uri(url, src_dir, warn)
        return f"{attr}={q}{uri}{q}" if uri else m.group(0)
    body = re.sub(r'(src|poster|href)=(["\'])([^"\']+\.(?:png|jpe?g|gif|webp|svg|avif|mp4|webm))\2', repl, body, flags=re.I)
    return inline_css_urls(body, src_dir, warn)


CREDIT_TXT = {"ja": ("画像・素材クレジット", "改変", "ライセンス"), "en": ("Image & asset credits", "modified", "License")}
PER_CREDIT_SLIDE = 9   # keeps each entry at a readable size


def apply_assets(body: str, src_dir: Path, cfg: dict, warn, extra_refs: str = "") -> str:
    """Resolve data-icon, add credit captions, append the credits slide, lint licences.
    Runs BEFORE image inlining so local paths are still visible."""
    cr_path = src_dir / "credits.json"
    ledger = A.load_credits(cr_path)
    used_icons: dict[str, dict] = {}

    def icon(m):
        tag, ref = m.group(0), m.group(1)
        try:
            if ":" in ref and not ref.lower().endswith(".svg"):
                svg, credit = A.icon_svg(ref)
                used_icons.setdefault(ref.split(":")[0], credit)
            else:
                svg = (src_dir / ref).read_text(encoding="utf-8")
        except (LookupError, OSError) as e:
            warn(f"icon {ref}: {e}")
            return tag
        return tag[:-len("></i>")] + ' aria-hidden="true">' + re.sub(r"<\?xml[^>]*>", "", svg).strip() + "</i>"
    body = re.sub(r'<i\b[^>]*\bdata-icon="([^"]+)"[^>]*></i>', icon, body)

    used = A.used_images(body + extra_refs)
    mode = cfg.get("credits", "auto")          # auto | slide | inline | off
    for u in used:
        rec = ledger.get(u)
        if rec is None:
            warn(f"image {u} has no licence record in credits.json – run: assets.py add {u} --own  (or record its licence)")
            continue
        if not rec.get("commercial_ok", True):
            warn(f"image {u} is {rec.get('license')} (non-commercial) – do not use in business/commercial settings")
    if mode in ("auto", "inline"):
        def caption(m):
            rec = ledger.get(m.group(2))
            if not rec or not rec.get("attribution_required"):
                return m.group(0)
            return m.group(0) + f'<span class="credit">{html.escape(rec.get("attribution", ""))}</span>'
        body = re.sub(r'(<img\b[^>]*\bsrc="([^"]+)"[^>]*>)', caption, body)
    third = [(u, ledger[u]) for u in used if u in ledger and ledger[u].get("license") and not ledger[u]["license"].startswith("Own")]
    third += [(f"iconset:{k}", v) for k, v in used_icons.items()]
    third_imgs = [t for t in third if not t[0].startswith("iconset:")]
    if mode in ("auto", "slide") and third_imgs:
        lang = "ja" if cfg.get("lang", "ja").startswith("ja") else "en"
        title, modw, licw = CREDIT_TXT[lang]
        items, seen = [], {}
        for u, r in third:
            # works needing per-work attribution stay separate; the rest are grouped by source+creator+licence
            if r.get("attribution_required"):
                key = (r.get("title"), r.get("creator"), r.get("source"), r.get("license"))
            else:
                key = ("__group__", r.get("creator"), r.get("source"), r.get("license"))
            if key in seen:
                prev = seen[key]
                if key[0] == "__group__" and r.get("title") and r["title"] not in prev["_titles"]:
                    prev["_titles"].append(r["title"])
                if r.get("modified") and r["modified"] not in prev.get("modified", ""):
                    prev["modified"] = "; ".join(x for x in [prev.get("modified", ""), r["modified"]] if x)
                continue
            seen[key] = dict(r, _path=u, _titles=[r.get("title")] if r.get("title") else [])
        for r in seen.values():
            if len(r["_titles"]) > 1:
                n = len(r["_titles"])
                r["title"] = f"{r.get('source') or r.get('creator')} の素材 {n} 点" if lang == "ja" else f"{n} items from {r.get('source') or r.get('creator')}"
                r["_list"] = ", ".join(re.sub(r"\s*\((photo|texture map|star map)\)", "", t) for t in r["_titles"])
                mods = sorted({m.split(" (")[0].strip() for m in (r.get("modified") or "").replace(";", ",").split(",") if m.strip()})
                r["modified"] = ", ".join(mods)
        for r in seen.values():
            u = r["_path"].replace("iconset:", "")
            who = " / ".join(x for x in [html.escape(r.get("creator", "")), html.escape(r.get("source", ""))] if x)
            lic = html.escape(r.get("license", ""))
            if r.get("license_url"):
                lic = f'<a href="{html.escape(r["license_url"])}">{lic}</a>'
            head = html.escape(r.get("title") or u)
            if r.get("source_url"):
                head = f'<a href="{html.escape(r["source_url"])}">{head}</a>'
            mod = f'<span class="mod">（{modw}: {html.escape(r["modified"])}）</span>' if r.get("modified") else ""
            lst = f'<span class="list">{html.escape(r["_list"])}</span>' if r.get("_list") else ""
            items.append(f"<li><b>{head}</b><span>{who} · {lic}</span>{lst}{mod}</li>")
        pages = [items[i:i + PER_CREDIT_SLIDE] for i in range(0, len(items), PER_CREDIT_SLIDE)]
        for k, pg in enumerate(pages, 1):
            suffix = f" ({k}/{len(pages)})" if len(pages) > 1 else ""
            note = f'\n  <p class="caption">{html.escape(cfg["credits_note"])}</p>' if cfg.get("credits_note") and k == len(pages) else ""
            body += (f'\n<section class="slide L-credits" data-chrome="off">\n  <div class="kicker">Credits</div>\n'
                     f'  <h2 class="headline">{title}{suffix}</h2>\n  <ul class="credits">{"".join(pg)}</ul>{note}\n</section>\n')
    return body


def lint(body: str, cfg: dict) -> tuple[list[str], list[str]]:
    errs, warns = [], []
    sections = re.findall(r"<section\b([^>]*)>(.*?)</section>", body, re.S)
    if not sections:
        errs.append("no <section class=\"slide\"> found")
    density = cfg.get("density", "speaker")
    for i, (attrs, inner) in enumerate(sections, 1):
        cls = re.search(r'class="([^"]*)"', attrs)
        classes = set(cls.group(1).split()) if cls else set()
        if "slide" not in classes:
            errs.append(f"slide {i}: <section> needs class=\"slide\"")
        lay = [c for c in classes if c.startswith("L-")]
        for c in lay:
            if c not in LAYOUTS:
                warns.append(f"slide {i}: unknown layout class {c} (known: {', '.join(sorted(LAYOUTS))})")
        tr = re.search(r'data-transition="([^"]*)"', attrs)
        if tr and tr.group(1) not in TRANSITIONS:
            errs.append(f"slide {i}: data-transition=\"{tr.group(1)}\" invalid ({', '.join(sorted(TRANSITIONS))})")
        for a in re.findall(r'data-(?:anim|stagger)="([^"]*)"', inner):
            if a and a not in ANIMS:
                errs.append(f"slide {i}: unknown animation \"{a}\" ({', '.join(sorted(ANIMS))})")
        morphs = re.findall(r'data-morph="([^"]+)"', inner)
        dup = {m for m in morphs if morphs.count(m) > 1}
        if dup:
            errs.append(f"slide {i}: duplicate data-morph key(s) {sorted(dup)} – keys must be unique per slide")
        if not (set(lay) & NO_HEADLINE_OK) and not re.search(r"<h[12]\b|class=\"[^\"]*headline", inner):
            warns.append(f"slide {i}: no <h2>/headline – every content slide should state its one message as a headline")
        if density == "speaker" and "<aside class=\"notes\">" not in inner and not classes & {"L-title", "L-credits"}:
            warns.append(f"slide {i}: no <aside class=\"notes\"> – speaker decks should carry what to SAY in notes")
        # clicks = distinct numbered steps + each bare data-step (elements sharing a number appear together)
        numbered = set(re.findall(r'\bdata-step="(\d+)"', inner))
        bare = len(re.findall(r'\bdata-step(?![-=])', inner))
        n_steps = len(numbered) + bare
        if n_steps > 7:
            warns.append(f"slide {i}: {n_steps} build steps – more than ~6 clicks per slide tires the audience; split the slide")
        anims = len(re.findall(r"data-anim=", inner)) + len(re.findall(r"data-stagger=", inner)) * 3
        if anims > 14:
            warns.append(f"slide {i}: {anims}+ animated elements – motion should guide the eye, not decorate everything")
        if re.search(r"<img(?![^>]*\balt=)", inner):
            warns.append(f"slide {i}: <img> without alt text")
        if re.search(r'style="[^"]*font-size:\s*(1\d|[1-9])px', inner):
            warns.append(f"slide {i}: inline font-size under 20px – unreadable from the back of the room")
    return errs, warns


def build(src_path: Path, out: Path | None, theme: str | None, font_mode: str, inline: bool, quiet=False) -> Path:
    log = (lambda *a: None) if quiet else print
    src = src_path.read_text(encoding="utf-8")
    cfg, deck_css, head_tags, body = split_source(src)
    theme = theme or cfg.get("theme", "washi")
    tpath = theme_path(theme, src_path.parent)
    theme_css = tpath.read_text(encoding="utf-8")

    warns: list[str] = []
    body = MK.expand(body, src_path.parent, warns.append)          # data-mock="er|sheet" → HTML (before icons are resolved)
    body = apply_assets(body, src_path.parent, cfg, warns.append, extra_refs=deck_css)
    if inline:
        body = inline_images(body, src_path.parent, warns.append)
        deck_css = inline_css_urls(deck_css, src_path.parent, warns.append)   # e.g. one shared background image, inlined once
    errs, w2 = lint(body, cfg)
    warns += w2

    specs = F.parse_theme_fonts(theme_css) + [F.FontSpec(f["family"], [str(x) for x in f["weights"]]) for f in cfg.get("fonts", [])]
    if font_mode == "embed":
        font_html = f"<style>/* embedded fonts (subset to this deck's characters) */\n{F.embed_css(specs, visible_text(body) + cfg.get('footer', '') + cfg.get('title', ''), log)}\n</style>"
    elif font_mode == "none":
        font_html = ""
    else:
        font_html = F.link_tags(specs)

    tokens = cfg.get("tokens", {})
    token_css = (":root{" + ";".join(f"{k}:{v}" for k, v in tokens.items()) + "}") if tokens else ""
    runtime_cfg = {k: cfg[k] for k in ("credits", "transition", "footer", "chrome", "density", "baseDelay", "autoGap", "staggerGap", "countDur") if k in cfg}
    runtime_cfg["lang"] = cfg.get("lang", "ja")
    title = html.escape(cfg.get("title", src_path.stem))
    desc = html.escape(cfg.get("description", ""))

    page = f"""<!DOCTYPE html>
<html lang="{html.escape(cfg.get('lang', 'ja'))}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<meta name="generator" content="slide-forge">
<meta name="author" content="{html.escape(cfg.get('author', ''))}">
{font_html}
{chr(10).join(head_tags)}
<style>
/* ===== Slide Forge runtime ===== */
{(RUNTIME / 'slides.css').read_text(encoding='utf-8')}
/* ===== Theme: {tpath.stem} ===== */
{theme_css}
/* ===== Deck tokens ===== */
{token_css}
/* ===== Deck CSS ===== */
{deck_css}
</style>
</head>
<body>
<div class="deck-viewport">
<main class="deck-stage" aria-live="polite">
{body}
</main>
</div>
<script>window.DECK_CONFIG = {json.dumps(runtime_cfg, ensure_ascii=False)};</script>
<script>
{(RUNTIME / 'slides.js').read_text(encoding='utf-8')}
</script>
</body>
</html>
"""
    out = out or src_path.with_name(src_path.name.replace(".src.html", ".html") if ".src." in src_path.name else src_path.stem + ".built.html")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")
    n = len(re.findall(r"<section\b", body))
    log(f"✓ built {out}  ({n} slides, theme={tpath.stem}, fonts={font_mode}, {out.stat().st_size / 1024:.0f} KB)")
    for w in warns:
        log(f"  ⚠ {w}")
    for e in errs:
        log(f"  ✗ {e}")
    if errs:
        log(f"✗ {len(errs)} lint error(s) – fix before checking/delivering")
    return out, errs


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src", type=Path)
    ap.add_argument("-o", "--out", type=Path)
    ap.add_argument("--theme", help="built-in theme name or path to a theme .css (overrides deck-config)")
    ap.add_argument("--fonts", choices=["link", "embed", "none"],
                    help="link = Google Fonts <link> (default); embed = offline, subset & inline; none = system fonts. "
                         "Default comes from deck-config \"font_mode\" or 'link'.")
    ap.add_argument("--no-inline-images", action="store_true", help="keep local images as relative links")
    ap.add_argument("--watch", action="store_true", help="rebuild whenever the source or a theme changes")
    a = ap.parse_args()
    if not a.src.is_file():
        sys.exit(f"✗ {a.src} not found")
    cfg, *_ = split_source(a.src.read_text(encoding="utf-8"))
    fmode = a.fonts or cfg.get("font_mode", "link")

    def once():
        return build(a.src, a.out, a.theme, fmode, not a.no_inline_images)

    out, errs = once()
    if a.watch:
        watched = [a.src, *THEMES.glob("*.css"), *RUNTIME.glob("*")]
        stamp = {p: p.stat().st_mtime for p in watched}
        print("… watching for changes (Ctrl+C to stop)")
        try:
            while True:
                time.sleep(0.6)
                for p in watched:
                    if p.stat().st_mtime != stamp[p]:
                        stamp = {q: q.stat().st_mtime for q in watched}
                        once()
                        break
        except KeyboardInterrupt:
            pass
    sys.exit(1 if errs else 0)


if __name__ == "__main__":
    main()
