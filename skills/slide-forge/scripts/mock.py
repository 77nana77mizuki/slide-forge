#!/usr/bin/env python3
"""Slide mockups: database diagrams (tables + relations), spreadsheet export screens
(Excel-style window with column letters, row numbers, old/new comparison, callouts), and
web app / smartphone screens with annotation notes (data-mock="app", see mock_app.py).

In a deck (preferred — build.py expands these, so the JSON stays the single source of truth):
    <div data-mock="er" data-src="db.json"></div>
    <script type="application/json" data-mock="sheet">{ … }</script>
Class/style/data-anim/data-delay/data-step written on the placeholder are kept on the result.

CLI (preview / generate specs):
    python scripts/mock.py er db.json --page -o er.html            # standalone preview page
    python scripts/mock.py sheet sheet.json -o sheet.fragment.html  # HTML fragment
    python scripts/mock.py diff --old old.csv --new new.csv --key 部品ID [--cols 部品名,材質] -o sheet.json

All geometry is in em of the mock's own font size ("font": px, default 24), so the generator can
place relation lines and callouts exactly. Cells never wrap: if a value is wider than its column,
check.py reports `overflow` — widen that column with "w" (em) in the spec.

ER spec:
{ "font": 24, "gap": 1.4, "indent": 3,
  "entities": [ {"id": "parts", "name": "部品マスター", "sub": "Parts Master", "icon": "tabler:settings",
                 "cols": ["部品ID", "部品名", "最終更新日時"], "pk": ["部品ID"], "fk": [],
                 "rows": [["P001", "Gear A", "2026-09-01"]],        # default: one row of "…"
                 "level": 0,                                         # auto layout: indent level (stacked top→bottom)
                 "x": 0, "y": 0, "w": 22} ],                         # optional explicit em position/width
  "links": [ {"from": "parts", "to": "conn", "label": "リレーション", "style": "down" | "side", "card": "1:N"} ] }

Sheet spec:
{ "font": 24, "title": "comparison_export.xlsx", "sheet": "Sheet1",
  "columns": [ {"name": "種別", "w": 4}, {"name": "部品名\\n(旧)", "tone": "old"}, {"name": "差分", "type": "marker"} ],
  "bands":   [ {"label": "旧データ", "from": "C", "to": "D", "tone": "old"} ],   # tones: old | new | accent | plain
  "rows":    [ {"status": "upd" | "new" | "del" | "same", "cells": ["更新", "P001", {"v": "Gear A+", "cls": "chg"}]} ],
  "blank": 3,                                                        # empty rows under the data
  "callouts": [ {"at": "I5", "text": "変更・追加が一目でわかる", "side": "top" | "bottom" | "left" | "right",
                 "dx": 0, "dy": 0, "step": false} ],
  "anim": true,
  "diff": { "key": "部品ID", "cols": ["部品名", "材質"], "old": [ {…} ], "new": [ {…} ],   # or "old_csv"/"new_csv"
            "layout": "groups" | "pairs", "only_changes": false, "labels": {"new": "新規", "upd": "更新", "del": "削除", "same": "―"} } }
When "diff" is given, columns/bands/rows are generated from it (explicit "columns"/"rows" are ignored).
"""
from __future__ import annotations

import argparse
import csv
import html
import json
import re
import sys
import unicodedata
from pathlib import Path

E = html.escape


# ─── text metrics (em of the mock font) ───────────────────────────────────────
def text_em(s: str) -> float:
    """Width in em. Per-class widths are the maxima measured in the browser across all 7 theme body fonts
    (bold included), so a cell sized from them never clips whichever theme is used."""
    w = 0.0
    for ch in str(s):
        if unicodedata.east_asian_width(ch) in ("W", "F", "A") or ord(ch) > 0x2E80:
            w += 1.0
        elif ch.isupper():
            w += 0.78
        elif ch.isdigit():
            w += 0.74
        elif ch == " ":
            w += 0.35
        elif ch in ".,:;!|'()[]-_/":
            w += 0.44
        else:
            w += 0.64
    return w


def lines_em(s: str) -> float:
    return max((text_em(x) for x in str(s).split("\n")), default=0.0)


def fmt(x: float) -> str:
    return f"{x:.3f}".rstrip("0").rstrip(".") or "0"


# ─── ER diagram ───────────────────────────────────────────────────────────────
ER = dict(pad=0.55, title=2.2, gap_title=0.35, row=1.9, cellpad=1.5, keybadge=2.6)


def entity_geometry(ent: dict) -> dict:
    cols = ent.get("cols", [])
    rows = ent["rows"] if "rows" in ent else [["…"] * len(cols)]      # "rows": [] → header only
    keys = set(ent.get("pk", [])) | set(ent.get("fk", []))
    widths = []
    for i, c in enumerate(cols):
        w = text_em(c) + (ER["keybadge"] if c in keys else 0)
        for r in rows:
            if i < len(r):
                w = max(w, text_em(r[i]))
        widths.append(max(w + ER["cellpad"], 3.2))
    if ent.get("col_w"):
        widths = [float(x) for x in ent["col_w"]]
    title_w = 2.4 + text_em(ent.get("name", "")) * 1.1 + (text_em(f"（{ent['sub']}）") * 1.0 if ent.get("sub") else 0)
    w = float(ent.get("w") or max(sum(widths), title_w) + 2 * ER["pad"])
    inner = w - 2 * ER["pad"]
    if sum(widths) < inner:                                      # spread spare width across columns
        extra = (inner - sum(widths)) / max(len(widths), 1)
        widths = [x + extra for x in widths]
    h = ER["pad"] * 2 + ER["title"] + ER["gap_title"] + ER["row"] * (1 + len(rows))
    return dict(w=w, h=h, widths=widths, rows=rows)


def render_er(spec: dict, attrs: dict | None = None) -> str:
    font = spec.get("font", 24)
    gap, indent = spec.get("gap", 1.4), spec.get("indent", 3.0)
    ents = spec["entities"]
    links = spec.get("links", [])
    row_layout = spec.get("layout") == "row"
    geo, y, x = {}, 0.0, 0.0
    for ent in ents:
        g = entity_geometry(ent)
        if row_layout:                                          # side by side, left → right
            lab = max((text_em(l.get("label", "")) for l in links if l.get("to") == ent["id"]), default=0)
            if geo:
                x += max(gap, lab + 1.2)
            g["x"] = float(ent.get("x", x))
            g["y"] = float(ent.get("y", float(ent.get("level", 0)) * indent + (1.6 if lab else 0)))
            x = g["x"] + g["w"]
        else:                                                   # stacked, top → bottom, indented by level
            g["x"] = float(ent["x"]) if "x" in ent else float(ent.get("level", 0)) * indent
            has_label = any(l.get("to") == ent["id"] and l.get("label") for l in links)
            g["y"] = float(ent["y"]) if "y" in ent else y + (1.3 if has_label and geo else 0)
            y = g["y"] + g["h"] + gap
        geo[ent["id"]] = g
    # leave room for the "down" link labels between stacked boxes
    W = max(g["x"] + g["w"] for g in geo.values()) + 0.2 + max((text_em(l.get("label", "")) + 1 for l in links), default=0) * (not row_layout)
    H = max(g["y"] + g["h"] for g in geo.values()) + 0.2

    paths, labels = [], []

    def head(x, y, dx, dy):
        s_, w_ = 0.55, 0.3                                        # arrowhead length / half-width (em)
        bx, by = x - dx * s_, y - dy * s_
        return f'<path d="M{fmt(x)} {fmt(y)} L{fmt(bx - dy * w_)} {fmt(by + dx * w_)} L{fmt(bx + dy * w_)} {fmt(by - dx * w_)} Z" fill="currentColor" stroke="none"/>'

    for ln in links:
        a, b = geo.get(ln["from"]), geo.get(ln["to"])
        if not a or not b:
            raise ValueError(f"link {ln}: unknown entity id")
        style = ln.get("style") or ("side" if b["x"] > a["x"] + 0.5 and b["y"] > a["y"] + a["h"] + 3 else "down")
        if style == "side":
            tx = a["x"] + 1.3
            ty = b["y"] + ER["pad"] + ER["title"] / 2
            d = f"M{fmt(tx)} {fmt(a['y'] + a['h'])} V{fmt(ty)} H{fmt(b['x'] - 0.45)}"
            tip = (b["x"] - 0.05, ty, 1, 0)
            lx, lyy = tx + 0.5, (a["y"] + a["h"] + ty) / 2
        else:
            lo, hi = max(a["x"], b["x"]) + 1.5, min(a["x"] + a["w"], b["x"] + b["w"]) - 1.5
            tx = min(max(b["x"] + b["w"] * 0.42, lo), hi) if hi > lo else b["x"] + 1.5
            y0, y1 = a["y"] + a["h"], b["y"]
            if y1 > y0:
                d = f"M{fmt(tx)} {fmt(y0)} V{fmt(y1 - 0.45)}"
                tip = (tx, y1 - 0.05, 0, 1)
                lx, lyy = tx + 0.6, (y0 + y1) / 2
            else:                                               # side by side: connect right edge → left edge
                ym = max(a["y"], b["y"]) + ER["pad"] + ER["title"] + ER["gap_title"] + ER["row"] / 2
                d = f"M{fmt(a['x'] + a['w'])} {fmt(ym)} H{fmt(b['x'] - 0.45)}"
                tip = (b["x"] - 0.05, ym, 1, 0)
                lx = (a["x"] + a["w"] + b["x"]) / 2 - text_em(ln.get("label", "")) / 2
                lyy = ym - 1.1
        paths.append(f'<path d="{d}" fill="none" stroke="currentColor" stroke-width=".11" stroke-linejoin="round"/>' + head(*tip))
        if ln.get("label"):
            labels.append(f'<div class="mk-link-label" style="left:{fmt(lx)}em;top:{fmt(lyy)}em">{E(ln["label"])}</div>')
        if ln.get("card"):
            c0, c1 = (ln["card"].split(":") + [""])[:2]
            labels.append(f'<div class="mk-card mk-chrome" style="left:{fmt(tx - 1.2)}em;top:{fmt(a["y"] + a["h"] + 0.1)}em">{E(c0)}</div>')

    anim = spec.get("anim", True)
    boxes = []
    for i, ent in enumerate(ents):
        g = geo[ent["id"]]
        pk, fk = set(ent.get("pk", [])), set(ent.get("fk", []))
        cols = ent.get("cols", [])
        ths = []
        for c in cols:
            badge = '<span class="mk-key">PK</span>' if c in pk else ('<span class="mk-key fk">FK</span>' if c in fk else "")
            ths.append(f"<th>{badge}{E(c)}</th>")
        trs = "".join("<tr>" + "".join(f"<td>{E(str(v))}</td>" for v in r) + "</tr>" for r in g["rows"])
        colg = "".join(f'<col style="width:{fmt(w)}em">' for w in g["widths"])
        icon = f'<i class="ico" data-icon="{E(ent["icon"])}"></i>' if ent.get("icon") else ""
        sub = f'<span class="mk-sub">（{E(ent["sub"])}）</span>' if ent.get("sub") else ""
        a = f' data-anim="up" data-delay="{150 + i * 170}"' if anim else ""
        boxes.append(
            f'<div class="mk-entity"{a} style="left:{fmt(g["x"])}em;top:{fmt(g["y"])}em;width:{fmt(g["w"])}em">'
            f'<div class="mk-title">{icon}<span class="mk-name">{E(ent.get("name", ent["id"]))}</span>{sub}</div>'
            f'<table><colgroup>{colg}</colgroup><thead><tr>{"".join(ths)}</tr></thead><tbody>{trs}</tbody></table></div>')
    draw = f' data-anim="draw" data-delay="{250 + len(ents) * 170}"' if anim else ""
    svg = (f'<svg class="mk-links" viewBox="0 0 {fmt(W)} {fmt(H)}" style="width:{fmt(W)}em;height:{fmt(H)}em"{draw} aria-hidden="true">'
           + "".join(paths) + "</svg>")
    return wrap("mk-er", attrs, f"--mk-font:{font}px;width:{fmt(W)}em;height:{fmt(H)}em", svg + "".join(boxes) + "".join(labels),
                label=spec.get("aria", "データベースのテーブルと関連の図"))


# ─── spreadsheet ──────────────────────────────────────────────────────────────
SH = dict(title=2.1, formula=1.9, letters=1.45, band=2.1, row=1.9, head_line=1.3, head_pad=0.7, rn=2.4, tabs=1.8)
STATUS_LABEL = {"new": "新規", "upd": "更新", "del": "削除", "same": "―"}


def col_letter(i: int) -> str:
    s = ""
    i += 1
    while i:
        i, r = divmod(i - 1, 26)
        s = chr(65 + r) + s
    return s


def col_index(ref) -> int:
    if isinstance(ref, int):
        return ref
    n = 0
    for ch in str(ref).upper():
        n = n * 26 + ord(ch) - 64
    return n - 1


def load_rows(v, base: Path) -> list[dict]:
    if isinstance(v, list):
        return v
    with open(base / v, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def diff_to_sheet(spec: dict, base: Path) -> dict:
    d = spec["diff"]
    key = d["key"]
    old = load_rows(d.get("old") if "old" in d else d["old_csv"], base)
    new = load_rows(d.get("new") if "new" in d else d["new_csv"], base)
    cols = d.get("cols") or [c for c in (new[0] if new else old[0]).keys() if c != key]
    lab = {**STATUS_LABEL, **d.get("labels", {})}
    om, nm = {str(r[key]): r for r in old}, {str(r[key]): r for r in new}
    order = list(nm.keys()) + [k for k in om if k not in nm]
    layout = d.get("layout", "groups")
    columns = [{"name": d.get("status_header", "種別")}, {"name": key}]
    if layout == "pairs":
        for c in cols:
            columns += [{"name": f"{c}\n(旧)", "tone": "old", "src": ("old", c)}, {"name": f"{c}\n(新)", "tone": "new", "src": ("new", c)}]
        columns.append({"name": d.get("marker_header", "差分"), "type": "marker"})
        bands = []
    else:
        columns += [{"name": f"{c}\n(旧)", "tone": "old", "src": ("old", c)} for c in cols]
        columns.append({"name": d.get("marker_header", "差分"), "type": "marker"})
        columns += [{"name": f"{c}\n(新)", "tone": "new", "src": ("new", c)} for c in cols]
        n = len(cols)
        bands = [{"label": d.get("old_label", "旧データ"), "from": 2, "to": 1 + n, "tone": "old"},
                 {"label": d.get("new_label", "新データ"), "from": 3 + n, "to": 2 + 2 * n, "tone": "new"}]
    rows = []
    for k in order:
        o, nw = om.get(k), nm.get(k)
        st = "new" if o is None else "del" if nw is None else ("upd" if any(str(o.get(c, "")) != str(nw.get(c, "")) for c in cols) else "same")
        if st == "same" and d.get("only_changes"):
            continue
        cells = [lab[st], k]
        for c in columns[2:]:
            if c.get("type") == "marker":
                cells.append("")
                continue
            side, name = c["src"]
            rec = o if side == "old" else nw
            v = "" if rec is None else str(rec.get(name, ""))
            changed = st == "upd" and o is not None and nw is not None and str(o.get(name, "")) != str(nw.get(name, ""))
            cells.append({"v": v, "cls": ("chg" if side == "new" else "was")} if changed else v)
        rows.append({"status": st, "cells": cells})
    out = {k: v for k, v in spec.items() if k != "diff"}
    out.update(columns=[{k: v for k, v in c.items() if k != "src"} for c in columns], bands=bands, rows=rows)
    return out


def render_sheet(spec: dict, attrs: dict | None = None, base: Path = Path(".")) -> str:
    if "diff" in spec:
        spec = diff_to_sheet(spec, base)
    font = spec.get("font", 24)
    cols = [c if isinstance(c, dict) else {"name": c} for c in spec["columns"]]
    rows = [r if isinstance(r, dict) else {"cells": r} for r in spec.get("rows", [])]
    bands = spec.get("bands", [])
    # column widths
    hk = max(0.92, 20 / font)
    widths = []
    for i, c in enumerate(cols):
        if c.get("w"):
            widths.append(float(c["w"]))
            continue
        w = lines_em(c.get("name", "")) * hk                           # header text: max(20px, .92em)
        for r in rows:
            cells = r.get("cells", [])
            if i < len(cells):
                v = cells[i]["v"] if isinstance(cells[i], dict) else cells[i]
                w = max(w, text_em(v))
        widths.append(max(w + 1.4, 2.6 if c.get("type") == "marker" else 3.2))
    head_lines = max((len(str(c.get("name", "")).split("\n")) for c in cols), default=1)
    head_h = SH["head_line"] * head_lines * hk + SH["head_pad"]
    heights = ([SH["band"]] if bands else []) + [head_h] + [SH["row"]] * (len(rows) + int(spec.get("blank", 0)))
    grid_w = SH["rn"] + sum(widths)
    top0 = SH["title"] + SH["formula"] + SH["letters"]

    tone = {}
    for c_i, c in enumerate(cols):
        if c.get("tone"):
            tone[c_i] = c["tone"]
    for b in bands:
        for c_i in range(col_index(b["from"]), col_index(b["to"]) + 1):
            tone.setdefault(c_i, b.get("tone", "plain"))
    focus = {}
    for co in spec.get("callouts", []):
        m = re.fullmatch(r"([A-Za-z]+)(\d+)", co["at"])
        if not m:
            raise ValueError(f"callout at={co['at']!r}: use a cell reference like E5")
        focus[(col_index(m.group(1)), int(m.group(2)))] = True

    def tcls(i, extra=""):
        t = tone.get(i)
        cl = (f"mk-tone-{t} " if t else "") + extra
        return f' class="{cl.strip()}"' if cl.strip() else ""

    rn = 0
    body = []
    if bands:
        rn += 1
        cells, i = [], 0
        spans = {col_index(b["from"]): b for b in bands}
        while i < len(cols):
            if i in spans:
                b = spans[i]
                n = col_index(b["to"]) - i + 1
                cells.append(f'<td colspan="{n}" class="mk-band-cell"><span class="mk-band mk-band-{E(b.get("tone", "plain"))}">{E(b["label"])}</span></td>')
                i += n
            else:
                cells.append("<td></td>")
                i += 1
        body.append(f'<tr class="mk-r-band" style="height:{fmt(SH["band"])}em"><th class="mk-rn mk-chrome">{rn}</th>{"".join(cells)}</tr>')
    rn += 1
    hdr = "".join(f'<th{tcls(i, "mk-h")}>{"<br>".join(E(x) for x in str(c.get("name", "")).split(chr(10)))}</th>' for i, c in enumerate(cols))
    body.append(f'<tr class="mk-r-head" style="height:{fmt(head_h)}em"><th class="mk-rn mk-chrome">{rn}</th>{hdr}</tr>')
    first_data = rn + 1
    data_trs = []
    for r in rows:
        rn += 1
        st = r.get("status", "")
        tds = []
        for i, c in enumerate(cols):
            cells = r.get("cells", [])
            cell = cells[i] if i < len(cells) else ""
            v, extra = (cell.get("v", ""), cell.get("cls", "")) if isinstance(cell, dict) else (cell, "")
            if c.get("type") == "marker":
                mark = {"upd": "変更", "new": "追加", "del": "削除"}.get(st)
                inner = f'<span class="mk-mark mk-mark-{st}" role="img" aria-label="{mark}"></span>' if mark else ""
                extra += " mk-marker"
            else:
                inner = E(str(v))
            if (i, rn) in focus:
                extra += " mk-focus"
            tds.append(f"<td{tcls(i, extra)}>{inner}</td>")
        data_trs.append(f'<tr class="mk-st-{E(st) if st else "none"}"><th class="mk-rn mk-chrome">{rn}</th>{"".join(tds)}</tr>')
    for _ in range(int(spec.get("blank", 0))):
        rn += 1
        data_trs.append(f'<tr class="mk-blank"><th class="mk-rn mk-chrome">{rn}</th>{"".join(f"<td{tcls(i)}></td>" for i in range(len(cols)))}</tr>')

    anim = spec.get("anim", True)
    tb_anim = ' data-stagger="fade" data-stagger-gap="90"' if anim else ""
    letters = "".join(f'<th class="mk-chrome">{col_letter(i)}</th>' for i in range(len(cols)))
    colg = f'<col style="width:{fmt(SH["rn"])}em">' + "".join(f'<col style="width:{fmt(w)}em">' for w in widths)
    grid = (f'<table class="mk-grid" style="width:{fmt(grid_w)}em"><colgroup>{colg}</colgroup>'
            f'<thead><tr class="mk-letters" style="height:{fmt(SH["letters"])}em"><th class="mk-corner"></th>{letters}</tr></thead>'
            f'<tbody>{"".join(body)}</tbody><tbody{tb_anim}>{"".join(data_trs)}</tbody></table>')

    # callouts (positions from the same geometry the table uses)
    row_top = {}
    y = top0
    for i, h in enumerate(heights):
        row_top[i + 1] = (y, h)
        y += h
    col_left = []
    x = SH["rn"]
    for w in widths:
        col_left.append(x)
        x += w
    outs = []
    for n, co in enumerate(spec.get("callouts", [])):
        m = re.fullmatch(r"([A-Za-z]+)(\d+)", co["at"])
        ci, ri = col_index(m.group(1)), int(m.group(2))
        if ci >= len(widths) or ri not in row_top:
            raise ValueError(f"callout at={co['at']}: outside the sheet ({col_letter(len(widths) - 1)}{len(heights)} is the last cell)")
        side = co.get("side", "top")
        cy, ch = row_top[ri]
        cx = col_left[ci] + widths[ci] / 2
        px, py = {"top": (cx, cy), "bottom": (cx, cy + ch), "left": (col_left[ci], cy + ch / 2), "right": (col_left[ci] + widths[ci], cy + ch / 2)}[side]
        px += float(co.get("dx", 0))
        py += float(co.get("dy", 0))
        if co.get("step"):
            a = f' data-step="{co["step"]}"' if isinstance(co["step"], int) and not isinstance(co["step"], bool) else " data-step"
        else:
            a = f' data-anim="pop" data-delay="{900 + n * 250}"' if anim else ""
        outs.append(f'<div class="mk-anchor mk-{side}" style="left:{fmt(px)}em;top:{fmt(py)}em"{a}><div class="mk-callout">{E(co["text"])}</div></div>')

    win_btns = '<span class="mk-winbtns" aria-hidden="true"><i></i><i></i><i></i></span>'
    title = (f'<div class="mk-titlebar" style="height:{fmt(SH["title"])}em"><span class="mk-appicon" aria-hidden="true"></span>'
             f'<span class="mk-filename">{E(spec.get("label", "出力ファイル: "))}{E(spec.get("title", "export.xlsx"))}</span>{win_btns}</div>')
    fbar = (f'<div class="mk-formula" style="height:{fmt(SH["formula"])}em"><span class="mk-namebox mk-chrome">{E(spec.get("cell", "A1"))}</span>'
            f'<span class="mk-fx mk-chrome">fx</span><span class="mk-fxval"></span></div>')
    tabs = f'<div class="mk-tabs" style="height:{fmt(SH["tabs"])}em"><span class="mk-tab mk-chrome">{E(spec.get("sheet", "Sheet1"))}</span></div>'
    total_h = top0 + sum(heights) + SH["tabs"]
    return wrap("mk-sheet", attrs, f"--mk-font:{font}px;width:{fmt(grid_w)}em;height:{fmt(total_h)}em",
                title + fbar + grid + tabs + "".join(outs), label=spec.get("aria", f"表計算ソフトで開いた {spec.get('title', 'export.xlsx')} の画面イメージ"))


# ─── placeholder handling ─────────────────────────────────────────────────────
def wrap(cls: str, attrs: dict | None, style: str, inner: str, label: str) -> str:
    attrs = dict(attrs or {})
    classes = (cls + " " + attrs.pop("class", "")).strip()
    st = style + (";" + attrs.pop("style") if attrs.get("style") else "")
    rest = "".join(f' {k}="{E(v)}"' for k, v in attrs.items())
    return f'<div class="{classes}" role="img" aria-label="{E(label)}" style="{st}"{rest}>{inner}</div>'


KEEP = ("class", "style", "data-anim", "data-delay", "data-dur", "data-step", "data-morph", "id")


def _attrs(tag: str) -> dict:
    return {k: html.unescape(v) for k, v in re.findall(r'([\w-]+)="([^"]*)"', tag) if k in KEEP}


def render(kind: str, spec: dict, attrs=None, base: Path = Path(".")) -> str:
    if kind == "er":
        return render_er(spec, attrs)
    if kind == "sheet":
        return render_sheet(spec, attrs, base)
    if kind == "app":
        import mock_app
        return mock_app.render_app(spec, attrs, wrap)
    raise ValueError(f"unknown mock kind {kind!r} (er | sheet | app)")


def expand(body: str, src_dir: Path, warn) -> str:
    """Replace <div data-mock=… data-src=…></div> and <script type=application/json data-mock=…> with rendered HTML."""
    def one(kind, spec_text, tag):
        try:
            return render(kind, json.loads(spec_text), _attrs(tag), src_dir)
        except (ValueError, KeyError, OSError, json.JSONDecodeError) as e:
            warn(f"mock {kind}: {e}")
            return f'<div class="mk-error">mock {E(kind)}: {E(str(e))}</div>'

    def from_script(m):
        return one(m.group(2), m.group(3), m.group(1))

    def from_div(m):
        tag = m.group(0)
        src = re.search(r'data-src="([^"]+)"', tag)
        if not src:
            warn("mock: data-src missing on <div data-mock>")
            return tag
        try:
            text = (src_dir / src.group(1)).read_text(encoding="utf-8")
        except OSError as e:
            warn(f"mock: {e}")
            return tag
        return one(m.group(1), text, tag.split(">", 1)[0])

    body = re.sub(r'(<script\b[^>]*\bdata-mock="(\w+)"[^>]*>)(.*?)</script>', from_script, body, flags=re.S)
    body = re.sub(r'<div\b[^>]*\bdata-mock="(\w+)"[^>]*>\s*</div>', from_div, body)
    return body


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for k in ("er", "sheet", "app"):
        p = sub.add_parser(k)
        p.add_argument("spec")
        p.add_argument("-o", "--out")
        p.add_argument("--page", action="store_true", help="wrap in a one-slide deck source (build it to preview)")
    p = sub.add_parser("diff", help="old/new CSV → sheet spec JSON with the comparison already worked out")
    p.add_argument("--old", required=True)
    p.add_argument("--new", required=True)
    p.add_argument("--key", required=True)
    p.add_argument("--cols", help="comma-separated columns to compare (default: all except key)")
    p.add_argument("--layout", choices=["groups", "pairs"], default="groups")
    p.add_argument("--only-changes", action="store_true")
    p.add_argument("--title", default="comparison_export.xlsx")
    p.add_argument("-o", "--out")
    a = ap.parse_args()
    if a.cmd == "diff":
        d = {"key": a.key, "old_csv": a.old, "new_csv": a.new, "layout": a.layout, "only_changes": a.only_changes}
        if a.cols:
            d["cols"] = [c.strip() for c in a.cols.split(",")]
        spec = diff_to_sheet({"title": a.title, "diff": d, "blank": 2}, Path("."))
        text = json.dumps(spec, ensure_ascii=False, indent=1)
    else:
        spec = json.loads(Path(a.spec).read_text(encoding="utf-8"))
        text = render(a.cmd, spec, base=Path(a.spec).parent)
        if a.page:
            text = ('<script type="application/json" id="deck-config">{"title":"mock preview","theme":"swiss","density":"reading"}</script>\n'
                    f'<section class="slide L-free" data-chrome="off"><div class="grow" style="display:grid;place-items:center">{text}</div></section>\n')
    if a.out:
        Path(a.out).write_text(text, encoding="utf-8")
        print(f"✓ {a.out}")
    else:
        print(text)


if __name__ == "__main__":
    main()
