#!/usr/bin/env python3
"""Outline → validate → scaffold.  The outline is the contract between story and build.

    python scripts/outline.py check outline.md             # ghost-deck + rule check
    python scripts/outline.py scaffold outline.md -o deck.src.html

outline.md format (see references/narrative.md):

    # 来期の開発方針
    - theme: blueprint
    - density: speaker            (speaker | reading)
    - audience: 技術部の全メンバー（約40名）
    - goal: 3つの重点施策に納得し、明日から動けること
    - minutes: 15
    - footer: TECH DIVISION 2026

    ## [L-title] 来期は「品質を仕組みで守る」一年にする
    sub: 技術部 全体会議 / 2026.10
    notes: …

    ## [L-stats] 手戻りの 6 割はレビューで防げていた
    - 62% | 設計起因の手戻り
    - 3.1日 | 1件あたりの平均対応
    notes: 数字の出典は品質月報 9月号
    source: 品質月報 2026年9月

Each "## [layout] headline" is one slide. The headline must be the slide's single message
(a claim, not a topic label). Bullets under it become the slide body.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path

HEADLINE_MAX = {"speaker": 34, "reading": 48}      # visible chars (JA) – ≈2 lines at 68px
BULLETS_MAX = {"speaker": 4, "reading": 7}
TOPIC_LABELS = re.compile(r"^(概要|背景|課題|目的|まとめ|今後|現状|目次|アジェンダ|agenda|overview|summary|background|introduction|conclusion)$", re.I)
KNOWN = {"L-title", "L-section", "L-statement", "L-bullets", "L-split", "L-cards", "L-stats", "L-compare", "L-quote",
         "L-image", "L-closing", "L-chart", "L-timeline", "L-flow", "L-code", "L-table", "L-agenda", "L-free"}
NO_CLAIM_NEEDED = {"L-title", "L-section", "L-closing", "L-quote", "L-agenda", "L-image"}


def vlen(s: str) -> int:
    cjk = len(re.findall(r"[　-ヿ㐀-鿿＀-￯]", s))
    return cjk + round((len(s) - cjk) / 2.2)


def parse(md: str) -> dict:
    deck = {"title": "", "meta": {}, "slides": []}
    cur = None
    for raw in md.splitlines():
        line = raw.rstrip()
        if not line.strip():
            continue
        if line.startswith("# ") and not deck["title"]:
            deck["title"] = line[2:].strip(); continue
        m = re.match(r"##\s*(?:\d+[.)]\s*)?\[(L-[\w-]+)(?:\s+([^\]]*))?\]\s*(.*)", line)
        if m:
            cur = {"layout": m.group(1), "mods": (m.group(2) or "").split(), "headline": m.group(3).strip(),
                   "bullets": [], "fields": {}}
            deck["slides"].append(cur); continue
        m = re.match(r"\s*([a-z_]+):\s*(.*)", line)
        if m and cur is not None and not line.lstrip().startswith("-"):
            cur["fields"][m.group(1)] = (cur["fields"].get(m.group(1), "") + " " + m.group(2)).strip(); continue
        m = re.match(r"-\s*([a-z_]+):\s*(.*)", line)
        if m and cur is None:
            deck["meta"][m.group(1)] = m.group(2).strip(); continue
        m = re.match(r"\s*[-*]\s+(.*)", line)
        if m and cur is not None:
            cur["bullets"].append(m.group(1).strip()); continue
        if cur is not None:   # continuation text
            cur["fields"]["body"] = (cur["fields"].get("body", "") + " " + line.strip()).strip()
    return deck


def check(deck: dict) -> tuple[list[str], list[str]]:
    errs, warns = [], []
    meta = deck["meta"]
    density = meta.get("density", "speaker")
    for k in ("audience", "goal"):
        if not meta.get(k):
            errs.append(f"deck: '- {k}:' is missing – a deck without a named audience and goal can't be judged")
    slides = deck["slides"]
    if not slides:
        errs.append("no slides (use '## [L-layout] headline')")
    if slides and slides[0]["layout"] != "L-title":
        warns.append("slide 1 is not L-title")
    mins = float(meta.get("minutes", 0) or 0)
    if mins and density == "speaker":
        content = sum(1 for s in slides if s["layout"] not in ("L-title", "L-section", "L-closing"))
        if content > mins * 1.6:
            warns.append(f"{content} content slides for {mins:g} min ≈ {60 * mins / content:.0f}s each – likely too many (aim ~1 per minute)")
        if content < mins * 0.5:
            warns.append(f"only {content} content slides for {mins:g} min – each will stay up a long time")
    run = 0
    for i, s in enumerate(slides, 1):
        lay, h = s["layout"], s["headline"]
        if lay not in KNOWN:
            errs.append(f"slide {i}: unknown layout {lay}")
        if not h:
            errs.append(f"slide {i}: empty headline")
        elif lay not in NO_CLAIM_NEEDED:
            if TOPIC_LABELS.match(h.strip("「」 ")):
                errs.append(f"slide {i}: headline \"{h}\" is a topic label – write the claim (what should the audience conclude?)")
            if vlen(h) > HEADLINE_MAX[density]:
                warns.append(f"slide {i}: headline is {vlen(h)} chars (> {HEADLINE_MAX[density]}) – tighten it")
        per_list = len(s["bullets"]) // 2 if lay == "L-compare" else len(s["bullets"])
        if per_list > BULLETS_MAX[density]:
            warns.append(f"slide {i}: {len(s['bullets'])} bullets (> {BULLETS_MAX[density]} for {density}) – split or cut")
        if density == "speaker" and "notes" not in s["fields"] and lay != "L-title":
            warns.append(f"slide {i}: no 'notes:' – write what you will SAY")
        if lay in ("L-stats", "L-chart") and "source" not in s["fields"]:
            warns.append(f"slide {i}: numbers without 'source:' – cite where the data comes from")
        vis = s["fields"].get("visual", "")
        img = s["fields"].get("image") or s["fields"].get("bg")
        if vis.startswith(("photo", "illustration", "image")) and not img:
            warns.append(f"slide {i}: visual '{vis}' planned but no image: yet – source it (slide-art-director / assets.py search → pick)")
        if lay == "L-image" and not img:
            errs.append(f"slide {i}: L-image needs 'image: img/…'")
        if img and deck.get("_dir") and not (deck["_dir"] / img).exists():
            warns.append(f"slide {i}: {img} does not exist yet")
        run = run + 1 if lay == "L-bullets" else 0
        if run >= 3:
            warns.append(f"slide {i}: 3 bullet slides in a row – vary the visual form (stats, compare, flow, statement)")
    return errs, warns


def ghost(deck: dict) -> str:
    out = [f"「{deck['title']}」 — ghost deck (headlines only; this should read as the whole argument)", ""]
    for i, s in enumerate(deck["slides"], 1):
        out.append(f"{i:>2}. {s['headline']}")
    return "\n".join(out)


# ------------------------------------------------------------------ scaffold
e = html.escape


ICON_RE = re.compile(r"^[a-z0-9-]+:[a-z0-9-]+$")


def split_pair(b: str) -> tuple[str, str]:
    return tuple(x.strip() for x in b.split("|", 1)) if "|" in b else (b, "")  # type: ignore


def split_icon(b: str) -> tuple[str, str, str]:
    """'tabler:robot | 見出し | 説明' → (icon, title, desc); icon optional."""
    parts = [x.strip() for x in b.split("|")]
    icon = parts.pop(0) if len(parts) > 1 and ICON_RE.match(parts[0]) else ""
    return icon, parts[0], " | ".join(parts[1:])


def ico(ref: str) -> str:
    return f'<i class="ico" data-icon="{e(ref)}"></i>' if ref else ""


def media_bg(f: dict, cls: str = "") -> str:
    src = f.get("bg") or ""
    return f'<div class="media-bg{(" " + cls) if cls else ""}"><img src="{e(src)}" alt="{e(f.get("alt", ""))}"></div>\n  ' if src else ""


def render(s: dict, idx: int) -> str:
    lay, h, b, f = s["layout"], e(s["headline"]), s["bullets"], s["fields"]
    mods = " ".join(s["mods"])
    kicker = f'<div class="kicker" data-anim="fade">{e(f["kicker"])}</div>' if "kicker" in f else ""
    head = f'<div class="head">{kicker}<h2 class="headline" data-anim="up">{h}</h2></div>'
    notes = f'\n  <aside class="notes">{e(f.get("notes", ""))}</aside>' if f.get("notes") else ""
    src = f'\n  <p class="source">出典: {e(f["source"])}</p>' if f.get("source") else ""
    attrs = f' class="slide {lay}{(" " + mods) if mods else ""}"'
    if lay == "L-title":
        inner = f'''{media_bg(f)}{kicker}
  <h1 class="hero" data-anim="up">{h}</h1>
  {f'<p class="lede" data-anim="up">{e(f["sub"])}</p>' if f.get("sub") else ""}'''
        attrs += ' data-chrome="off"'
    elif lay == "L-section":
        inner = f'<div class="sec-no" data-anim="from-left">{e(f.get("no", f"{idx:02d}"))}</div>\n  <h2 data-anim="up">{h}</h2>'
        attrs = attrs.replace('class="slide L-section', 'class="slide L-section invert') if "invert" not in mods else attrs
    elif lay in ("L-statement", "L-closing"):
        if lay == "L-closing":
            attrs += ' data-chrome="off"'
        inner = f'{media_bg(f, "full")}{kicker}\n  <p class="statement" data-anim="up">{h}</p>' + (f'\n  <p class="lede" data-anim="up">{e(f["sub"])}</p>' if f.get("sub") else "")
    elif lay == "L-quote":
        inner = f'<blockquote class="quote" data-anim="blur">{h}</blockquote>' + (f'\n  <p class="quote-by" data-anim="fade">— {e(f["by"])}</p>' if f.get("by") else "")
    elif lay == "L-stats":
        cells = "".join(f'<div class="stat{" hl" if k == 0 else ""}"><div class="value" data-count>{e(v)}</div><div class="label">{e(l)}</div></div>'
                        for k, (v, l) in enumerate(split_pair(x) for x in b))
        inner = f'{head}\n  <div class="stats" style="--cols:{max(1, min(4, len(b)))}" data-stagger="up">{cells}</div>'
    elif lay == "L-image":
        img = f.get("image") or f.get("bg") or ""
        inner = (f'<img src="{e(img)}" alt="{e(f.get("alt", s["headline"]))}">\n  <div class="overlay"><h2 class="headline" data-anim="up">{h}</h2>'
                 + (f'<p class="caption" data-anim="fade">{e(f["sub"])}</p>' if f.get("sub") else "") + "</div>")
    elif lay == "L-cards":
        cells = "".join(f'<div class="card">{ico(ic)}<h3>{e(t)}</h3>{f"<p>{e(d)}</p>" if d else ""}</div>' for ic, t, d in (split_icon(x) for x in b))
        inner = f'{head}\n  <div class="cards" style="--cols:{max(1, min(4, len(b)))}" data-stagger="up">{cells}</div>'
    elif lay == "L-timeline":
        cells = "".join(f'<div class="t"><div class="when">{e(w)}</div><h3>{e(t)}</h3></div>' for w, t in (split_pair(x) for x in b))
        inner = f'{head}\n  <div class="timeline grow" style="--cols:{max(1, len(b))};align-content:center" data-stagger="up">{cells}</div>'
    elif lay == "L-flow":
        nodes = []
        for k, x in enumerate(b):
            t, d = split_pair(x)
            if k:
                nodes.append('<div class="arrow" data-step></div>')
            nodes.append(f'<div class="node" data-step><h3>{e(t)}</h3>{f"<p>{e(d)}</p>" if d else ""}</div>')
        inner = f'{head}\n  <div class="flow grow" style="align-items:center">{"".join(nodes)}</div>'
    elif lay == "L-chart":
        vals = [split_pair(x) for x in b]
        nums = [float(re.sub(r"[^\d.]", "", v) or 0) for _, v in vals]
        mx = max(nums) if nums and max(nums) > 0 else 1
        rows = "".join(f'<div class="bar{" hl" if n == mx else ""}" style="--v:{n / mx:.3f}"><span class="k">{e(k)}</span><div class="track"><div class="fill"></div></div><span class="v" data-count>{e(v)}</span></div>'
                       for (k, v), n in zip(vals, nums))
        inner = f'{head}\n  <div class="grow" style="display:flex;align-items:center" data-anim="fade"><div class="bars">{rows}</div></div>'
    elif lay == "L-compare":
        half = max(1, len(b) // 2)
        left, right = b[:half], b[half:]
        ls = f.get("left", "Before"); rs = f.get("right", "After")
        inner = (f'{head}\n  <div class="compare">'
                 f'<div class="side" data-anim="from-left"><div class="label">{e(ls)}</div><ul class="points">{"".join(f"<li>{e(x)}</li>" for x in left)}</ul></div>'
                 f'<div class="side after" data-anim="from-right" data-delay="350"><div class="label">{e(rs)}</div><ul class="points">{"".join(f"<li>{e(x)}</li>" for x in right)}</ul></div></div>')
    elif lay == "L-split":
        img = f.get("image")
        right = (f'<div class="frame" style="height:640px"><img class="photo" src="{e(img)}" alt="{e(f.get("alt", ""))}"></div>' if img
                 else "<!-- TODO visual: image / diagram / chart -->")
        inner = (f'{head}\n  <div class="col" data-anim="from-left"><ul class="points">{"".join(f"<li>{e(x)}</li>" for x in b)}</ul></div>'
                 f'\n  <div class="col" data-anim="from-right">{right}</div>')
    else:  # L-bullets, L-agenda, L-free …
        numbered = " numbered big" if lay == "L-agenda" else ""
        inner = f'{head}\n  <div class="body"><ul class="points{numbered}" data-stagger="up">{"".join(f"<li>{e(x)}</li>" for x in b)}</ul></div>'
        if lay == "L-agenda":
            attrs = attrs.replace("L-agenda", "L-bullets L-agenda")
    if f.get("bg") and lay not in ("L-title", "L-statement", "L-closing", "L-image"):
        inner = media_bg(f, "full") + inner
    return f"<!-- {idx} -->\n<section{attrs}>\n  {inner}{src}{notes}\n</section>"


def scaffold(deck: dict) -> str:
    m = deck["meta"]
    cfg = {"title": deck["title"], "author": m.get("author", ""), "lang": m.get("lang", "ja"), "theme": m.get("theme", "washi"),
           "transition": m.get("transition", "fade"), "footer": m.get("footer", ""), "density": m.get("density", "speaker")}
    body = "\n\n".join(render(s, i) for i, s in enumerate(deck["slides"], 1))
    return (f'<script type="application/json" id="deck-config">\n{json.dumps(cfg, ensure_ascii=False, indent=2)}\n</script>\n\n'
            f"<style>\n  /* deck-specific CSS */\n</style>\n\n{body}\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check"); c.add_argument("outline", type=Path)
    s = sub.add_parser("scaffold"); s.add_argument("outline", type=Path); s.add_argument("-o", "--out", type=Path)
    s.add_argument("--force", action="store_true", help="scaffold even when the outline has errors")
    a = ap.parse_args()
    deck = parse(a.outline.read_text(encoding="utf-8"))
    deck["_dir"] = a.outline.resolve().parent
    errs, warns = check(deck)
    print(ghost(deck)); print()
    for w in warns:
        print(f"  ⚠ {w}")
    for x in errs:
        print(f"  ✗ {x}")
    print(f"{'✗' if errs else '✓'} outline: {len(deck['slides'])} slides, {len(errs)} errors, {len(warns)} warnings")
    if a.cmd == "scaffold":
        if errs and not a.force:
            sys.exit("✗ fix the outline errors first (or --force)")
        out = a.out or a.outline.with_name("deck.src.html")
        if out.exists():
            sys.exit(f"✗ {out} exists – refusing to overwrite hand-edited work (delete it or choose -o)")
        out.write_text(scaffold(deck), encoding="utf-8")
        print(f"✓ scaffolded {out} – now design each slide (layouts.md / motion.md), then build.py")
    sys.exit(1 if errs else 0)


if __name__ == "__main__":
    main()
