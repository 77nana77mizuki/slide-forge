"""Web app / smartphone screen mockups for slides (data-mock="app"). Imported by mock.py.

Spec (all sizes in em of "font", default 20px):
{ "device": "browser" | "phone", "font": 20, "brand": "#2563eb",
  "url": "https://example.com/dashboard", "tab": "AXIS Pro - ダッシュボード",
  "app": {"name": "AXIS Pro", "logo": "A"}, "sidebar": "dark" | "light" | false,
  "nav": [ {"icon": "tabler:home", "label": "概要", "active": true}, … ],
  "title": "ダッシュボード", "actions": ["tabler:bell", "tabler:settings"], "user": "山田",
  "width": 44,              # content width (browser); phone is fixed
  "cols": 3,                # widget grid columns
  "widgets": [ {"id": "kpi", "type": "kpi", "span": 2, "h": 5, "dark": true, "title": "…", …}, … ],
  "notes":    [ {"to": "kpi", "side": "left" | "right", "title": "管理者画面", "items": ["リアルタイム集計"], "tone": "accent" | "muted", "step": 1} ],
  "callouts": [ {"to": "kpi", "text": "…", "side": "top" | "bottom" | "left" | "right", "dx": 0, "dy": 0, "step": 1} ],
  "gutter": 13,             # width of the note columns (em) — 0 when there are no notes on that side
  "anim": true }

Widget types and their fields:
  kpi      items: [{label, value, delta}]                      (dark: true → brand-coloured panel)
  line     labels: [...], series: [{name, values}], max        (area line chart; first series is the brand colour)
  bars     labels: [...], series: [{name, values}], max        (grouped vertical bars)
  donut    value: 0–100, center, legend: [{label, value}]
  list     rows: [{name, sub, badge}]                           (initial avatars — never photos of real people)
  progress rows: [{label, value (0–100)}]
  gantt    units: ["4月", …], tasks: [{name, start, len, done}], today
  table    columns: [...], rows: [[...]]
  form     fields: [{label, value, placeholder}], button
  profile  name, role, lines: [...]
  text     body
New rows start whenever the next widget no longer fits; "row_break": true forces one.
"""
from __future__ import annotations

import html

E = html.escape


def fmt(x: float) -> str:
    return f"{x:.3f}".rstrip("0").rstrip(".") or "0"


DEV = {
    "browser": dict(tabbar=2.3, addr=2.4, header=3.0, sidebar=10.0, pad=1.0, gap=0.8, width=44.0),
    "phone": dict(frame=0.7, status=1.7, header=2.8, bottomnav=3.2, pad=0.8, gap=0.7, width=17.6, radius=2.6),
}
DEFAULT_H = dict(kpi=5.6, line=11.0, bars=11.0, donut=10.0, list=10.0, progress=10.0, gantt=10.0,
                 table=9.0, form=11.0, profile=10.0, text=6.0)


def initials(name: str) -> str:
    s = str(name).strip()
    return s[:1] if s else "?"


def ico(ref: str, cls: str = "") -> str:
    return f'<i class="ico {cls}" data-icon="{E(ref)}"></i>' if ref else ""


# ─── widget bodies ────────────────────────────────────────────────────────────
def chart_svg(w: dict, kind: str) -> str:
    series = w.get("series") or [{"values": w.get("values", [])}]
    labels = w.get("labels", [])
    n = max((len(s.get("values", [])) for s in series), default=0) or 1
    vmax = float(w.get("max") or max((max(s.get("values", [0]) or [0]) for s in series), default=1) or 1) * 1.08
    parts = []
    for gy in (0.25, 0.5, 0.75):
        parts.append(f'<line x1="0" x2="100" y1="{fmt(40 * gy)}" y2="{fmt(40 * gy)}" class="mk-grid-line"/>')
    if kind == "line":
        for si, s in enumerate(series):
            vals = s.get("values", [])
            if not vals:
                continue
            step = 100 / max(len(vals) - 1, 1)
            pts = [(i * step, 40 - 38 * (v / vmax)) for i, v in enumerate(vals)]
            line = " ".join(f"{fmt(x)},{fmt(y)}" for x, y in pts)
            cls = "s1" if si == 0 else "s2"
            if si == 0:
                parts.append(f'<polygon points="0,40 {line} 100,40" class="mk-area"/>')
            parts.append(f'<polyline points="{line}" class="mk-line {cls}"/>')
    else:
        k = len(series)
        slot = 100 / n
        bw = slot * 0.62 / k
        for si, s in enumerate(series):
            for i, v in enumerate(s.get("values", [])):
                h = 38 * (v / vmax)
                x = i * slot + slot * 0.19 + si * bw
                parts.append(f'<rect x="{fmt(x)}" y="{fmt(40 - h)}" width="{fmt(bw * 0.9)}" height="{fmt(h)}" class="mk-bar {"s1" if si == 0 else "s2"}"/>')
    svg = f'<svg class="mk-chart" viewBox="0 0 100 40" preserveAspectRatio="none" aria-hidden="true">{"".join(parts)}</svg>'
    lab = "".join(f"<span>{E(str(x))}</span>" for x in labels)
    legend = ""
    if len(series) > 1 or series[0].get("name"):
        legend = '<div class="mk-legend">' + "".join(
            f'<span class="{"s1" if i == 0 else "s2"}">{E(s.get("name", ""))}</span>' for i, s in enumerate(series)) + "</div>"
    return f'{legend}{svg}<div class="mk-axis">{lab}</div>'


def widget_body(w: dict) -> str:
    t = w.get("type", "text")
    if t == "kpi":
        cells = "".join(
            f'<div class="mk-kpi-item"><div class="mk-kpi-label">{E(str(i.get("label", "")))}</div>'
            f'<div class="mk-kpi-value">{E(str(i.get("value", "")))}</div>'
            + (f'<div class="mk-kpi-delta">{E(str(i["delta"]))}</div>' if i.get("delta") else "") + "</div>"
            for i in w.get("items", []))
        return f'<div class="mk-kpi">{cells}</div>'
    if t in ("line", "bars"):
        return chart_svg(w, "line" if t == "line" else "bars")
    if t == "donut":
        v = float(w.get("value", 60))
        leg = "".join(f'<li><b>{E(str(x.get("value", "")))}</b> {E(str(x.get("label", "")))}</li>' for x in w.get("legend", []))
        return (f'<div class="mk-donut-wrap"><div class="mk-donut" style="--p:{fmt(v)}"><span>{E(str(w.get("center", f"{int(v)}%")))}</span></div>'
                f'<ul class="mk-legend-list">{leg}</ul></div>')
    if t == "list":
        rows = "".join(
            f'<div class="mk-row"><span class="mk-avatar">{E(initials(r.get("name", "")))}</span>'
            f'<span class="mk-row-text"><b>{E(str(r.get("name", "")))}</b>'
            + (f'<small>{E(str(r["sub"]))}</small>' if r.get("sub") else "") + "</span>"
            + (f'<span class="mk-badge">{E(str(r["badge"]))}</span>' if r.get("badge") else "") + "</div>"
            for r in w.get("rows", []))
        return f'<div class="mk-list">{rows}</div>'
    if t == "progress":
        rows = "".join(
            f'<div class="mk-prog"><span class="mk-prog-label">{E(str(r.get("label", "")))}</span>'
            f'<span class="mk-prog-track"><i style="width:{fmt(float(r.get("value", 0)))}%"></i></span>'
            f'<span class="mk-prog-val">{E(str(r.get("value", "")))}%</span></div>'
            for r in w.get("rows", []))
        return f'<div class="mk-progs">{rows}</div>'
    if t == "gantt":
        units = w.get("units", [])
        n = max(len(units), 1)
        head = '<div class="mk-g-head"><span></span><span class="mk-g-units">' + "".join(f"<i>{E(str(u))}</i>" for u in units) + "</span></div>"
        rows = []
        for tk in w.get("tasks", []):
            left = 100 * float(tk.get("start", 0)) / n
            width = 100 * float(tk.get("len", 1)) / n
            done = float(tk.get("done", 0))
            rows.append(f'<div class="mk-g-row"><span class="mk-g-name">{E(str(tk.get("name", "")))}</span><span class="mk-g-track">'
                        f'<i class="mk-g-bar" style="left:{fmt(left)}%;width:{fmt(width)}%"><b style="width:{fmt(done)}%"></b></i></span></div>')
        today = ""
        if w.get("today") is not None:
            today = f'<span class="mk-g-today" style="--x:{fmt(100 * float(w["today"]) / n)}"></span>'
        return f'<div class="mk-gantt">{head}<div class="mk-g-body">{"".join(rows)}{today}</div></div>'
    if t == "table":
        th = "".join(f"<th>{E(str(c))}</th>" for c in w.get("columns", []))
        tr = "".join("<tr>" + "".join(f"<td>{E(str(v))}</td>" for v in r) + "</tr>" for r in w.get("rows", []))
        return f'<table class="mk-apptable"><thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table>'
    if t == "form":
        f = "".join(
            f'<label class="mk-field"><span>{E(str(x.get("label", "")))}</span>'
            f'<span class="mk-input{" ph" if not x.get("value") else ""}">{E(str(x.get("value") or x.get("placeholder", "")))}</span></label>'
            for x in w.get("fields", []))
        btn = f'<span class="mk-btn">{E(str(w["button"]))}</span>' if w.get("button") else ""
        return f'<div class="mk-form">{f}{btn}</div>'
    if t == "profile":
        lines = "".join(f"<small>{E(str(x))}</small>" for x in w.get("lines", []))
        return (f'<div class="mk-profile"><span class="mk-avatar lg">{E(initials(w.get("name", "")))}</span>'
                f'<b>{E(str(w.get("name", "")))}</b><small>{E(str(w.get("role", "")))}</small>{lines}</div>')
    return f'<p class="mk-text">{E(str(w.get("body", "")))}</p>'


# ─── layout ───────────────────────────────────────────────────────────────────
def layout_widgets(widgets: list, cols: int, width: float, gap: float) -> tuple[dict, float]:
    colw = (width - gap * (cols - 1)) / cols
    pos, x_col, y, row_h = {}, 0, 0.0, 0.0
    for i, w in enumerate(widgets):
        span = min(int(w.get("span", 1)), cols)
        h = float(w.get("h", DEFAULT_H.get(w.get("type", "text"), 8)))
        if x_col + span > cols or (w.get("row_break") and x_col):
            y += row_h + gap
            x_col, row_h = 0, 0.0
        x = x_col * (colw + gap)
        pos[w.get("id", f"w{i}")] = dict(x=x, y=y, w=span * colw + (span - 1) * gap, h=h)
        x_col += span
        row_h = max(row_h, h)
    return pos, y + row_h


def render_app(spec: dict, attrs: dict | None, wrap) -> str:
    dev = spec.get("device", "browser")
    if dev not in DEV:
        raise ValueError(f"device {dev!r}: use browser | phone")
    D = DEV[dev]
    font = spec.get("font", 20)
    widgets = spec.get("widgets", [])
    cols = int(spec.get("cols", 3 if dev == "browser" else 1))
    notes = spec.get("notes", [])
    anim = spec.get("anim", True)

    if dev == "browser":
        side = D["sidebar"] if spec.get("sidebar", "dark") else 0.0
        cw = float(spec.get("width", D["width"]))
        pos, ch = layout_widgets(widgets, cols, cw, D["gap"])
        nav_h = 4.2 + 2.3 * len(spec.get("nav", []))
        body_h = max(ch + 2 * D["pad"], nav_h if side else 0)
        dev_w = side + cw + 2 * D["pad"]
        dev_h = D["tabbar"] + D["addr"] + D["header"] + body_h
        cx0, cy0 = side + D["pad"], D["tabbar"] + D["addr"] + D["header"] + D["pad"]
    else:
        side = 0.0
        cw = float(spec.get("width", D["width"]))
        pos, ch = layout_widgets(widgets, 1, cw, D["gap"])
        dev_w = cw + 2 * D["pad"] + 2 * D["frame"]
        dev_h = 2 * D["frame"] + D["status"] + D["header"] + ch + 2 * D["pad"] + D["bottomnav"]
        cx0, cy0 = D["frame"] + D["pad"], D["frame"] + D["status"] + D["header"] + D["pad"]

    # note columns
    nk = 1.2                                                     # note text is 1.2× the mock font
    # note column width: from the longest title / item (note text is nk× the mock font) unless given
    from mock import text_em
    auto = max([text_em(n.get("title", "")) * nk + 1.6 * nk for n in notes] +
               [(text_em(x) + 1.0) * nk + 1.3 * nk for n in notes for x in n.get("items", [])] + [8.0])
    gut = float(spec.get("gutter", round(auto + 0.4, 1)))
    lg = gut if any(n.get("side", "left") == "left" for n in notes) else 0.0
    rg = gut if any(n.get("side") == "right" for n in notes) else 0.0
    ngap = 1.6
    ox = lg + (ngap if lg else 0)                                # device origin inside the mock
    W = ox + dev_w + (ngap + rg if rg else 0)

    def box(wid, dy=0.0):
        p = pos.get(wid)
        if not p:
            raise ValueError(f"'to': {wid!r} is not a widget id ({', '.join(pos)})")
        return ox + cx0 + p["x"], dy + cy0 + p["y"], p["w"], p["h"]

    def place(dy):
        out, H = [], dev_h + dy
        for side_name in ("left", "right"):
            placed = []
            for n in (n for n in notes if n.get("side", "left") == side_name):
                nh = (2.0 + 1.55 * len(n.get("items", [])) + (0.7 if n.get("items") else 0)) * nk
                if "y" in n:
                    want = float(n["y"])
                elif n.get("to"):
                    bx, by, bw, bh = box(n["to"], dy)
                    want = by + bh / 2 - nh / 2
                else:
                    want = 0.0
                placed.append([n, max(want, 0.0), nh])
            placed.sort(key=lambda t: t[1])
            y = 0.0
            for item in placed:
                item[1] = max(item[1], y)
                y = item[1] + item[2] + 0.9
            if placed:
                H = max(H, y - 0.9)
            out += [(side_name, *t) for t in placed]
        return out, H

    placed, H = place(0.0)
    dy = max(0.0, (H - dev_h) / 2) if spec.get("center_device", True) else 0.0
    if dy:
        placed, H = place(dy)
    H = max(H, dev_h + dy)

    note_html, lines = [], []
    counters = {"left": 0, "right": 0}
    for side_name, n, ny, nh in placed:
        i = counters[side_name]
        counters[side_name] += 1
        nx = 0.0 if side_name == "left" else ox + dev_w + ngap
        tone = n.get("tone", "accent")
        items = "".join(f"<li>{E(str(x))}</li>" for x in n.get("items", []))
        if n.get("step"):
            a = f' data-step="{n["step"]}"' if isinstance(n["step"], int) and not isinstance(n["step"], bool) else " data-step"
            la = a
        else:
            a = f' data-anim="{"from-left" if side_name == "left" else "from-right"}" data-delay="{900 + i * 220}"' if anim else ""
            la = f' data-anim="fade" data-delay="{1100 + i * 220}"' if anim else ""
        note_html.append(
            f'<div class="mk-note mk-note-{E(tone)}" style="left:{fmt(nx)}em;top:{fmt(ny)}em;width:{fmt(gut)}em"{a}>'
            f'<div class="mk-note-title">{E(str(n.get("title", "")))}</div>'
            + (f'<ul>{items}</ul>' if items else "") + "</div>")
        if n.get("to"):
            bx, by, bw, bh = box(n["to"], dy)
            sy = ny + min(1.0 * nk, nh / 2)                       # leave from the title pill
            if side_name == "left":                                # end on the panel's edge, never on its text
                sx, tx = nx + gut, bx
            else:
                sx, tx = nx, bx + bw
            ty = by + min(bh / 2, 1.6)
            lines.append(f'<svg class="mk-leaders" viewBox="0 0 {{W}} {{H}}" style="width:{{W}}em;height:{{H}}em" aria-hidden="true"{la}>'
                         f'<path d="M{fmt(sx)} {fmt(sy)} L{fmt(tx)} {fmt(ty)}" class="mk-leader"/>'
                         f'<circle cx="{fmt(tx)}" cy="{fmt(ty)}" r=".32" class="mk-leader-dot"/></svg>')

    # widgets
    wh = []
    for i, w in enumerate(widgets):
        wid = w.get("id", f"w{i}")
        p = pos[wid]
        title = f'<div class="mk-w-title">{E(str(w["title"]))}{"<span class=mk-w-more>⋯</span>" if w.get("more", True) else ""}</div>' if w.get("title") else ""
        a = ""
        wh.append(f'<div class="mk-w mk-w-{E(w.get("type", "text"))}{" dark" if w.get("dark") else ""}"{a} '
                  f'style="left:{fmt(cx0 + p["x"])}em;top:{fmt(dy + cy0 + p["y"])}em;width:{fmt(p["w"])}em;height:{fmt(p["h"])}em">'
                  f'{title}<div class="mk-w-body">{widget_body(w)}</div></div>')

    # callouts pinned to widgets
    outs = []
    for n, co in enumerate(spec.get("callouts", [])):
        bx, by, bw, bh = box(co["to"], dy)
        s = co.get("side", "top")
        px, py = {"top": (bx + bw / 2, by), "bottom": (bx + bw / 2, by + bh), "left": (bx, by + bh / 2), "right": (bx + bw, by + bh / 2)}[s]
        px += float(co.get("dx", 0))
        py += float(co.get("dy", 0))
        if co.get("step"):
            a = f' data-step="{co["step"]}"' if isinstance(co["step"], int) and not isinstance(co["step"], bool) else " data-step"
        else:
            a = f' data-anim="pop" data-delay="{1200 + n * 250}"' if anim else ""
        outs.append(f'<div class="mk-anchor mk-{s}" style="left:{fmt(px)}em;top:{fmt(py)}em"{a}><div class="mk-callout">{E(co["text"])}</div></div>')

    # chrome
    brand = spec.get("brand", "#2563eb")
    app = spec.get("app", {})
    name, logo = app.get("name", ""), app.get("logo", initials(app.get("name", "A")))
    if dev == "browser":
        tab = (f'<div class="mk-b-tabbar" style="height:{fmt(D["tabbar"])}em"><span class="mk-b-tab"><span class="mk-favicon">{E(logo)}</span>'
               f'<span class="mk-b-tabtext">{E(str(spec.get("tab", name)))}</span><span class="mk-b-x">×</span></span>'
               f'<span class="mk-b-plus">+</span><span class="mk-winbtns dark" aria-hidden="true"><i></i><i></i><i></i></span></div>')
        addr = (f'<div class="mk-b-addr" style="height:{fmt(D["addr"])}em"><span class="mk-b-navbtns">{ico("tabler:arrow-left")}{ico("tabler:arrow-right")}{ico("tabler:refresh")}</span>'
                f'<span class="mk-b-url">{ico("tabler:lock")}<span>{E(str(spec.get("url", "https://example.com/")))}</span></span>'
                f'<span class="mk-b-navbtns">{ico("tabler:star")}{ico("tabler:dots")}</span></div>')
        side_html = ""
        if side:
            navs = "".join(f'<div class="mk-nav{" on" if x.get("active") else ""}">{ico(x.get("icon", ""))}<span>{E(str(x.get("label", "")))}</span></div>'
                           for x in spec.get("nav", []))
            side_html = (f'<div class="mk-side mk-side-{E(str(spec.get("sidebar", "dark")))}" style="top:{fmt(D["tabbar"] + D["addr"])}em;width:{fmt(side)}em;height:{fmt(dev_h - D["tabbar"] - D["addr"])}em">'
                         f'<div class="mk-brand"><span class="mk-logo">{E(logo)}</span><b>{E(name)}</b></div>{navs}</div>')
        acts = "".join(ico(x) for x in spec.get("actions", []))
        user = f'<span class="mk-avatar sm">{E(initials(spec["user"]))}</span>' if spec.get("user") else ""
        header = (f'<div class="mk-app-head" style="left:{fmt(side)}em;top:{fmt(D["tabbar"] + D["addr"])}em;width:{fmt(dev_w - side)}em;height:{fmt(D["header"])}em">'
                  f'<b>{E(str(spec.get("title", "")))}</b><span class="mk-acts">{acts}{user}</span></div>')
        device = (f'<div class="mk-device mk-browser" style="left:{fmt(ox)}em;top:{fmt(dy)}em;width:{fmt(dev_w)}em;height:{fmt(dev_h)}em">'
                  f'{tab}{addr}{side_html}{header}</div>')
    else:
        bn = "".join(f'<span class="{"on" if x.get("active") else ""}">{ico(x.get("icon", ""))}</span>' for x in spec.get("nav", []))
        device = (f'<div class="mk-device mk-phone" style="left:{fmt(ox)}em;top:{fmt(dy)}em;width:{fmt(dev_w)}em;height:{fmt(dev_h)}em;--fr:{fmt(D["frame"])}em">'
                  f'<div class="mk-p-status" style="top:{fmt(D["frame"])}em;height:{fmt(D["status"])}em"><span>9:41</span><span class="mk-p-notch"></span><span class="mk-p-bat"></span></div>'
                  f'<div class="mk-app-head" style="left:{fmt(D["frame"])}em;top:{fmt(D["frame"] + D["status"])}em;width:{fmt(dev_w - 2 * D["frame"])}em;height:{fmt(D["header"])}em">'
                  f'<b>{E(str(spec.get("title", name)))}</b><span class="mk-acts">{"".join(ico(x) for x in spec.get("actions", []))}</span></div>'
                  f'<div class="mk-p-nav" style="left:{fmt(D["frame"])}em;bottom:{fmt(D["frame"])}em;width:{fmt(dev_w - 2 * D["frame"])}em;height:{fmt(D["bottomnav"])}em">{bn}</div></div>')

    svg = "".join(l.replace("{W}", fmt(W)).replace("{H}", fmt(H)) for l in lines)
    wa = ' data-anim="fade" data-delay="300"' if anim else ""
    wlayer = f'<div class="mk-wlayer" style="left:{fmt(ox)}em;top:0;width:{fmt(dev_w)}em;height:{fmt(H)}em"{wa}>{"".join(wh)}</div>'
    label = spec.get("aria", f"{name or 'Web アプリ'}の画面イメージ" + ("（スマートフォン）" if dev == "phone" else ""))
    return wrap(f"mk-app mk-dev-{dev}", attrs, f"--mk-font:{font}px;--brand:{brand};width:{fmt(W)}em;height:{fmt(H)}em",
                device + wlayer + svg + "".join(note_html) + "".join(outs), label=label)
