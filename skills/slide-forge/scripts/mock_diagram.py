"""Diagrams for slides, imported by mock.py:
  data-mock="arch"  — architecture / data-flow diagram: nodes on a grid, edges routed automatically,
                      data packets that travel along the edges, edges and nodes revealed click by click
  data-mock="seq"   — sequence diagram: actors, lifelines, messages revealed one click at a time
  data-mock="japan" — Japan tile map (47 prefectures as equal tiles): values → colour scale, highlights, pins

arch: { "font": 22, "cell": [11, 6.5],                          # grid cell size (em)
        "nodes": [ {"id": "web", "label": "Web 画面", "sub": "React", "icon": "tabler:browser", "x": 0, "y": 0,
                    "kind": "box" | "db" | "user" | "ext", "step": 2} ],
        "edges": [ {"from": "web", "to": "api", "label": "REST", "step": 1, "flow": true, "dashed": false, "back": false} ] }
seq:  { "font": 22, "gap": 13, "row": 2.7,
        "actors": [ {"id": "u", "label": "利用者", "icon": "tabler:user"} ],
        "messages": [ {"from": "u", "to": "api", "label": "ログイン", "reply": false, "step": true} ] }   # step defaults to true
japan:{ "font": 20, "tile": 2.8, "values": {"福岡": 120, "東京": 300}, "unit": "件", "levels": 5,
        "highlight": ["福岡"], "pins": [ {"pref": "福岡", "text": "本社", "side": "left", "step": 1} ],
        "legend": true, "title": "…" }
"""
from __future__ import annotations

import html

E = html.escape


def fmt(x: float) -> str:
    return f"{x:.3f}".rstrip("0").rstrip(".") or "0"


def step_attr(x) -> str:
    if x is True or x == "":
        return " data-step"
    if isinstance(x, int) and not isinstance(x, bool):
        return f' data-step="{x}"'
    return ""


def arrowhead(x, y, dx, dy, s=0.55, w=0.3):
    bx, by = x - dx * s, y - dy * s
    return f'<path d="M{fmt(x)} {fmt(y)} L{fmt(bx - dy * w)} {fmt(by + dx * w)} L{fmt(bx + dy * w)} {fmt(by - dx * w)} Z" class="dg-head"/>'


# ─── architecture ─────────────────────────────────────────────────────────────
def render_arch(spec: dict, attrs, wrap, text_em) -> str:
    font = spec.get("font", 22)
    cw, chh = (spec.get("cell") or [11, 6.5])
    nodes = spec.get("nodes", [])
    nh = float(spec.get("node_h", 3.6))
    anim = spec.get("anim", True)
    geo = {}
    for n in nodes:
        span = float(n.get("span", 1))
        w = float(n.get("w", cw * 0.74 + cw * (span - 1)))
        cx = float(n["x"]) * cw + cw * span / 2
        cy = float(n["y"]) * chh + chh / 2
        geo[n["id"]] = dict(cx=cx, cy=cy, w=w, h=nh, x=cx - w / 2, y=cy - nh / 2)
    W = max(g["x"] + g["w"] for g in geo.values()) + cw * 0.1
    H = max(g["y"] + g["h"] for g in geo.values()) + chh * 0.15

    def side_point(g, tx, ty):
        """Where a line towards (tx, ty) leaves box g (axis-aligned: left/right/top/bottom)."""
        dx, dy = tx - g["cx"], ty - g["cy"]
        if abs(dx) * g["h"] >= abs(dy) * g["w"]:
            return (g["x"] + g["w"] if dx > 0 else g["x"], g["cy"], 1 if dx > 0 else -1, 0)
        return (g["cx"], g["y"] + g["h"] if dy > 0 else g["y"], 0, 1 if dy > 0 else -1)

    edges_html = []
    for j, e in enumerate(spec.get("edges", [])):
        a, b = geo[e["from"]], geo[e["to"]]
        off = float(e.get("offset", 0.35 if e.get("back") or any(
            x["from"] == e["to"] and x["to"] == e["from"] for x in spec.get("edges", [])) else 0))
        if e.get("back"):
            off = -off
        same_row = abs(a["cy"] - b["cy"]) < 0.5
        same_col = abs(a["cx"] - b["cx"]) < 0.5
        if same_row or same_col:
            sx, sy, _, _ = side_point(a, b["cx"], b["cy"])
            tx, ty, _, _ = side_point(b, a["cx"], a["cy"])
            if same_row:
                sy += off
                ty += off
            else:
                sx += off
                tx += off
            ux, uy = (1 if tx > sx else -1, 0) if same_row else (0, 1 if ty > sy else -1)
            pts = [(sx, sy), (tx - ux * 0.45, ty - uy * 0.45)]
            tip = (tx, ty, ux, uy)
            mid = ((sx + tx) / 2, (sy + ty) / 2 - (0.75 if same_row else 0))
        else:                                                    # elbow: horizontal out of a, vertical into b
            sx = a["x"] + a["w"] if b["cx"] > a["cx"] else a["x"]
            sy = a["cy"] + off
            tx = b["cx"] + off
            ty = b["y"] if b["cy"] > a["cy"] else b["y"] + b["h"]
            uy = 1 if ty > sy else -1
            pts = [(sx, sy), (tx, sy), (tx, ty - uy * 0.45)]
            tip = (tx, ty, 0, uy)
            mid = ((sx + tx) / 2, sy - 0.75)
        d = "M" + " L".join(f"{fmt(x)} {fmt(y)}" for x, y in pts)
        full = "M" + " L".join(f"{fmt(x * font)} {fmt(y * font)}" for x, y in pts + [(tip[0], tip[1])])
        st = step_attr(e.get("step"))
        how = "fade" if e.get("dashed") else "draw"          # dashes would be eaten by the stroke-draw animation
        a_ = st + f' data-anim="{how}"' if st else (f' data-anim="{how}" data-delay="{500 + j * 180}"' if anim else "")
        svg = (f'<svg class="dg-svg" viewBox="0 0 {fmt(W)} {fmt(H)}" style="width:{fmt(W)}em;height:{fmt(H)}em" aria-hidden="true">'
               f'<path d="{d}" class="dg-edge{" dashed" if e.get("dashed") else ""}"/>{arrowhead(*tip)}</svg>')
        lab = ""
        if e.get("label"):
            lab = f'<span class="dg-elabel" style="left:{fmt(mid[0])}em;top:{fmt(mid[1])}em">{E(e["label"])}</span>'
        pk = ""
        if e.get("flow", True):
            pk = "".join(f'<i class="dg-pkt" style="offset-path:path(\'{full}\');animation-delay:{k * 0.9:.1f}s"></i>' for k in range(2))
        edges_html.append(f'<div class="dg-e"{a_}>{svg}{lab}{pk}</div>')

    nodes_html = []
    for i, n in enumerate(nodes):
        g = geo[n["id"]]
        st = step_attr(n.get("step"))
        a_ = st or (f' data-anim="pop" data-delay="{150 + i * 110}"' if anim else "")
        icon = f'<i class="ico" data-icon="{E(n["icon"])}"></i>' if n.get("icon") else ""
        sub = f'<small>{E(n["sub"])}</small>' if n.get("sub") else ""
        nodes_html.append(f'<div class="dg-node dg-{E(n.get("kind", "box"))}{" hl" if n.get("hl") else ""}"{a_} '
                          f'style="left:{fmt(g["x"])}em;top:{fmt(g["y"])}em;width:{fmt(g["w"])}em;height:{fmt(g["h"])}em">'
                          f'{icon}<span class="dg-ntext"><b>{E(n.get("label", n["id"]))}</b>{sub}</span></div>')
    label = spec.get("aria", "構成図: " + "、".join(n.get("label", n["id"]) for n in nodes))
    return wrap("mk-diagram mk-arch", attrs, f"--mk-font:{font}px;width:{fmt(W)}em;height:{fmt(H)}em",
                "".join(edges_html) + "".join(nodes_html), label=label)


# ─── sequence ─────────────────────────────────────────────────────────────────
def render_seq(spec: dict, attrs, wrap, text_em) -> str:
    font = spec.get("font", 22)
    gap = float(spec.get("gap", 13))
    row = float(spec.get("row", 2.7))
    actors = spec.get("actors", [])
    msgs = spec.get("messages", [])
    head_h = 3.2
    xs = {a["id"]: gap / 2 + i * gap for i, a in enumerate(actors)}
    W = gap * len(actors)
    y0 = head_h + 1.6
    H = y0 + row * len(msgs) + 0.8
    parts = []
    for a in actors:
        x = xs[a["id"]]
        parts.append(f'<svg class="dg-svg" viewBox="0 0 {fmt(W)} {fmt(H)}" style="width:{fmt(W)}em;height:{fmt(H)}em" aria-hidden="true">'
                     f'<line x1="{fmt(x)}" x2="{fmt(x)}" y1="{fmt(head_h)}" y2="{fmt(H)}" class="dg-life"/></svg>')
        icon = f'<i class="ico" data-icon="{E(a["icon"])}"></i>' if a.get("icon") else ""
        bw = min(gap * 0.82, max(text_em(a.get("label", "")) + 3.2, 7))
        parts.append(f'<div class="dg-node dg-actor" style="left:{fmt(x - bw / 2)}em;top:0;width:{fmt(bw)}em;height:{fmt(head_h)}em">'
                     f'{icon}<span class="dg-ntext"><b>{E(a.get("label", a["id"]))}</b></span></div>')
    for i, m in enumerate(msgs):
        y = y0 + row * i
        a, b = xs[m["from"]], xs[m["to"]]
        st = step_attr(m.get("step", True))
        if a == b:                                               # self message: a small loop
            d = f"M{fmt(a)} {fmt(y - 0.5)} H{fmt(a + 2.2)} V{fmt(y + 0.5)} H{fmt(a + 0.45)}"
            tip = (a, y + 0.5, -1, 0)
            lx, full = a + 2.6, f"M{fmt(a * font)} {fmt((y - 0.5) * font)} H{fmt((a + 2.2) * font)} V{fmt((y + 0.5) * font)} H{fmt(a * font)}"
            lab = f'<span class="dg-mlabel" style="left:{fmt(lx)}em;top:{fmt(y)}em;transform:translate(0,-50%)">{E(m.get("label", ""))}</span>'
        else:
            u = 1 if b > a else -1
            d = f"M{fmt(a)} {fmt(y)} H{fmt(b - u * 0.45)}"
            tip = (b, y, u, 0)
            full = f"M{fmt(a * font)} {fmt(y * font)} H{fmt(b * font)}"
            lab = f'<span class="dg-mlabel" style="left:{fmt((a + b) / 2)}em;top:{fmt(y - 0.75)}em">{E(m.get("label", ""))}</span>'
        svg = (f'<svg class="dg-svg" viewBox="0 0 {fmt(W)} {fmt(H)}" style="width:{fmt(W)}em;height:{fmt(H)}em" aria-hidden="true">'
               f'<path d="{d}" class="dg-edge{" dashed" if m.get("reply") else ""}"/>{arrowhead(*tip)}</svg>')
        pk = f'<i class="dg-pkt once" style="offset-path:path(\'{full}\')"></i>'
        ma = st or (' data-anim="fade"' if spec.get("anim", True) else "")
        parts.append(f'<div class="dg-e dg-msg"{ma}>{svg}{lab}{pk}</div>')
    label = spec.get("aria", "シーケンス図: " + "、".join(m.get("label", "") for m in msgs))
    return wrap("mk-diagram mk-seq", attrs, f"--mk-font:{font}px;width:{fmt(W)}em;height:{fmt(H)}em", "".join(parts), label=label)


# ─── Japan tile map ───────────────────────────────────────────────────────────
JP_TILES = {
    "北海道": (12, 0), "青森": (12, 1), "秋田": (11, 2), "岩手": (12, 2), "山形": (11, 3), "宮城": (12, 3),
    "石川": (8, 3), "富山": (9, 3), "新潟": (10, 3),
    "福井": (7, 4), "岐阜": (8, 4), "長野": (9, 4), "群馬": (10, 4), "栃木": (11, 4), "福島": (12, 4),
    "京都": (6, 5), "滋賀": (7, 5), "愛知": (8, 5), "山梨": (9, 5), "埼玉": (10, 5), "茨城": (11, 5),
    "島根": (3, 5), "鳥取": (4, 5), "兵庫": (5, 5),
    "大阪": (6, 6), "奈良": (7, 6), "三重": (8, 6), "静岡": (9, 6), "東京": (10, 6), "千葉": (11, 6),
    "山口": (2, 6), "広島": (3, 6), "岡山": (4, 6), "和歌山": (6, 7), "神奈川": (10, 7),
    "佐賀": (0, 6), "福岡": (1, 6),
    "愛媛": (3, 7), "香川": (4, 7), "徳島": (5, 7), "高知": (4, 8),
    "長崎": (0, 7), "熊本": (1, 7), "大分": (2, 7), "鹿児島": (1, 8), "宮崎": (2, 8),
    "沖縄": (0, 9),
}
assert len(JP_TILES) == 47 and len(set(JP_TILES.values())) == 47


def pref_key(name: str) -> str:
    n = str(name).strip()
    if n in JP_TILES:
        return n
    for suf in ("県", "府", "都"):
        if n.endswith(suf) and n[:-1] in JP_TILES:
            return n[:-1]
    raise ValueError(f"unknown prefecture {name!r}")


def short(name: str) -> str:
    return name if len(name) <= 2 else ("北海道" if name == "北海道" else name[:2])


def render_japan(spec: dict, attrs, wrap, text_em) -> str:
    font = spec.get("font", 20)
    ts = float(spec.get("tile", 2.8))
    g = float(spec.get("gap", 0.22))
    step = ts + g
    vals = {pref_key(k): float(v) for k, v in spec.get("values", {}).items()}
    lv = int(spec.get("levels", 5))
    vmin, vmax = (min(vals.values()), max(vals.values())) if vals else (0, 1)
    hl = {pref_key(x) for x in spec.get("highlight", [])}
    unit = spec.get("unit", "")
    anim = spec.get("anim", True)
    W, H = 13 * step, 10 * step - g
    tiles = []
    for name, (c, r) in JP_TILES.items():
        cls = "jp-tile"
        wide = name == "北海道"                               # 3 characters: give it two tiles' width
        style = f"left:{fmt((c - 1) * step if wide else c * step)}em;top:{fmt(r * step)}em;width:{fmt(ts + step if wide else ts)}em;height:{fmt(ts)}em"
        if name in vals:
            k = 0 if vmax == vmin else min(lv - 1, int((vals[name] - vmin) / (vmax - vmin) * lv))
            cls += f" jp-v jp-l{k}" + (" dark" if (k + 1) / lv > 0.55 else "")
            style += f";--lv:{fmt((k + 1) / lv)}"
        if name in hl:
            cls += " hl"
        a = f' data-anim="pop" data-delay="{100 + (c + r) * 35}"' if anim else ""
        lab = "北海道" if name == "北海道" else short(name)
        tiles.append(f'<div class="{cls}"{a} style="{style}" title="{E(name)}{": " + E(f"{vals[name]:,.0f}{unit}") if name in vals else ""}">'
                     f'<span>{E(lab)}</span></div>')
    pins = []
    for i, p in enumerate(spec.get("pins", [])):
        c, r = JP_TILES[pref_key(p["pref"])]
        side = p.get("side", "right")
        cx, cy = c * step + ts / 2, r * step + ts / 2
        px, py = {"top": (cx, r * step), "bottom": (cx, r * step + ts), "left": (c * step, cy), "right": (c * step + ts, cy)}[side]
        st = step_attr(p.get("step")) if p.get("step") else (f' data-anim="pop" data-delay="{1100 + i * 250}"' if anim else "")
        pins.append(f'<div class="mk-anchor mk-{side}" style="left:{fmt(px)}em;top:{fmt(py)}em"{st}><div class="mk-callout">{E(p.get("text", p["pref"]))}</div></div>')
    legend = ""
    if vals and spec.get("legend", True):
        cells = "".join(f'<i class="jp-l{k}" style="--lv:{fmt((k + 1) / lv)}"></i>' for k in range(lv))
        legend = (f'<div class="jp-legend" style="left:0;top:{fmt(1.3 * step if spec.get("title") else 0.2 * step)}em">'
                  f'<span>{E(f"{vmin:,.0f}{unit}")}</span><span class="jp-scale">{cells}</span><span>{E(f"{vmax:,.0f}{unit}")}</span></div>')
    title = f'<div class="jp-title" style="left:0;top:0">{E(spec["title"])}</div>' if spec.get("title") else ""
    label = spec.get("aria", "日本地図（都道府県のタイル）" + ("：" + "、".join(f"{k} {v:,.0f}{unit}" for k, v in sorted(vals.items(), key=lambda t: -t[1])[:5]) if vals else ""))
    return wrap("mk-diagram mk-japan", attrs, f"--mk-font:{font}px;width:{fmt(W)}em;height:{fmt(H)}em",
                title + "".join(tiles) + legend + "".join(pins), label=label)
