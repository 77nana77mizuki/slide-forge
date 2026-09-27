"""Annotated charts for slides (data-mock="chart"). Imported by mock.py.

{ "type": "bar" | "hbar" | "line" | "area" | "scatter", "font": 24, "w": 40, "h": 18,   # size in em
  "labels": ["4月", "5月", …],
  "series": [ {"name": "今期", "values": [...]}, {"name": "前期", "values": [...]} ],   # scatter: "points": [[x, y, "label"], …]
  "min": 0, "max": 100, "unit": "%", "ticks": 4, "values": true,        # value labels on bars / line ends
  "highlight": ["8月"],                   # bars: only these keep the accent colour (the rest go grey)
  "sort": "desc", "top": 5,               # bars: sort by the first series, keep the first N
  "id": "sales", "morph": true,           # bars get data-morph keys "chart-sales-<label>-<series>" → they move between slides
  "series_steps": true,                   # 2nd+ series appear one click at a time
  "annotations": [
     {"type": "target", "value": 80, "label": "目標 80%"},
     {"type": "point", "at": "8月", "series": 0, "label": "新製品の発売"},
     {"type": "band", "from": "6月", "to": "8月", "label": "キャンペーン"},
     {"type": "note", "at": "4月", "value": 120, "label": "…"},
     … each may carry "step": true | n  (otherwise it fades in after the chart) ] }
"""
from __future__ import annotations

import html
import math

E = html.escape


def fmt(x: float) -> str:
    return f"{x:.3f}".rstrip("0").rstrip(".") or "0"


def nice_max(v: float) -> float:
    if v <= 0:
        return 1.0
    e = 10 ** math.floor(math.log10(v))
    for m in (1, 1.2, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10):
        if m * e >= v:
            return m * e
    return 10 * e


def num_label(v: float, unit: str) -> str:
    s = f"{v:,.0f}" if abs(v) >= 10 or v == int(v) else f"{v:,.1f}"
    return s + unit


def step_attr(x) -> str:
    if x is True or x == "":
        return " data-step"
    if isinstance(x, int) and not isinstance(x, bool):
        return f' data-step="{x}"'
    return ""


def render_chart(spec: dict, attrs, wrap, text_em) -> str:
    t = spec.get("type", "bar")
    font = spec.get("font", 24)
    W, H = float(spec.get("w", 40)), float(spec.get("h", 18))
    unit = spec.get("unit", "")
    labels = list(spec.get("labels", []))
    series = [dict(s) for s in spec.get("series", [])]
    anim = spec.get("anim", True)
    cid = spec.get("id", "")
    hl = set(str(x) for x in spec.get("highlight", []))

    if t in ("bar", "hbar") and (spec.get("sort") or spec.get("top")):
        order = list(range(len(labels)))
        if spec.get("sort"):
            order.sort(key=lambda i: series[0]["values"][i], reverse=spec["sort"] != "asc")
        if spec.get("top"):
            order = order[: int(spec["top"])]
        labels = [labels[i] for i in order]
        for s in series:
            s["values"] = [s["values"][i] for i in order]

    allv = [v for s in series for v in s.get("values", [])]
    if t == "scatter":
        pts = [p for s in series for p in s.get("points", [])]
        xs, ys = [p[0] for p in pts] or [0, 1], [p[1] for p in pts] or [0, 1]
        xmin, xmax = float(spec.get("xmin", 0)), float(spec.get("xmax", nice_max(max(xs) * 1.05)))
        allv = ys
    vmin = float(spec.get("min", 0 if t in ("bar", "hbar") or min(allv or [0]) >= 0 else min(allv)))
    ann_vals = [a.get("value") for a in spec.get("annotations", []) if a.get("value") is not None]
    vmax = float(spec.get("max", nice_max(max(allv + ann_vals + [1]) * 1.08)))
    ticks = int(spec.get("ticks", 4))

    # plot box (em)
    ylab_w = max(text_em(num_label(vmax, unit)), text_em(num_label(vmin, unit))) * 0.9 + 0.8
    if t == "hbar":
        cat_w = max((text_em(x) for x in labels), default=2) + 1.0
        L, R, T, B = cat_w, 3.2, 1.2, 1.6
    else:
        L, R, T, B = ylab_w, 1.2 + (max((text_em(s.get("name", "")) for s in series), default=0) * 0.9 if t in ("line", "area") else 0), 2.0, 2.0
    pw, ph = W - L - R, H - T - B

    def vy(v):                     # value → y (vertical charts)
        return T + ph * (1 - (v - vmin) / (vmax - vmin))

    def vx(v):                     # value → x (hbar)
        return L + pw * (v - vmin) / (vmax - vmin)

    n = max(len(labels), 1)
    parts, htmlp, svgs = [], [], []

    def cat_x(i):
        return L + pw * (i + 0.5) / n

    def idx(at):
        if isinstance(at, int):
            return at
        return labels.index(str(at)) if str(at) in labels else 0

    # grid + tick labels
    for k in range(ticks + 1):
        v = vmin + (vmax - vmin) * k / ticks
        if t == "hbar":
            x = vx(v)
            parts.append(f'<line x1="{fmt(x)}" x2="{fmt(x)}" y1="{fmt(T)}" y2="{fmt(T + ph)}" class="ch-grid"/>')
            htmlp.append(f'<span class="ch-tick ch-tick-x" style="left:{fmt(x)}em;top:{fmt(T + ph + 0.35)}em">{E(num_label(v, unit))}</span>')
        elif t != "scatter" or True:
            y = vy(v)
            parts.append(f'<line x1="{fmt(L)}" x2="{fmt(L + pw)}" y1="{fmt(y)}" y2="{fmt(y)}" class="ch-grid{" ch-base" if k == 0 else ""}"/>')
            htmlp.append(f'<span class="ch-tick" style="right:{fmt(W - L + 0.4)}em;top:{fmt(y)}em">{E(num_label(v, unit))}</span>')

    bars = []
    if t == "bar":
        k = len(series)
        slot = pw / n
        bw = slot * 0.62 / k
        for si, s in enumerate(series):
            st = step_attr(si) + ' data-anim="wipe-up"' if spec.get("series_steps") and si > 0 else ""
            for i, v in enumerate(s.get("values", [])):
                x = L + i * slot + slot * 0.19 + si * bw
                y0, y1 = vy(max(v, vmin)), vy(vmin)
                muted = hl and labels[i] not in hl
                cls = f"ch-bar s{min(si, 3)}" + (" muted" if muted else "") + (" hl" if labels[i] in hl else "")
                key = f' data-morph="chart-{E(cid)}-{E(labels[i])}-{si}"' if cid and spec.get("morph") else ""
                grow = "" if key or st else " ch-grow"
                bars.append(f'<div class="{cls}{grow}"{key}{st} style="left:{fmt(x)}em;top:{fmt(y0)}em;width:{fmt(bw * 0.92)}em;height:{fmt(y1 - y0)}em;--i:{i}"></div>')
                if spec.get("values", n <= 12):
                    vk = f' data-morph="chart-{E(cid)}-{E(labels[i])}-{si}-v"' if key else ""
                    bars.append(f'<span class="ch-val{" muted" if muted else ""}{" hl" if labels[i] in hl else ""}{grow and " ch-fade"}"{vk}{st} '
                                f'style="left:{fmt(x + bw * 0.46)}em;top:{fmt(y0)}em;--i:{i}">{E(num_label(v, unit))}</span>')
        for i, lab in enumerate(labels):
            htmlp.append(f'<span class="ch-cat{" hl" if lab in hl else ""}" style="left:{fmt(cat_x(i))}em;top:{fmt(T + ph + 0.35)}em">{E(lab)}</span>')
    elif t == "hbar":
        k = len(series)
        slot = ph / n
        bh = slot * 0.64 / k
        for si, s in enumerate(series):
            st = step_attr(si) + ' data-anim="wipe"' if spec.get("series_steps") and si > 0 else ""
            for i, v in enumerate(s.get("values", [])):
                y = T + i * slot + slot * 0.18 + si * bh
                muted = hl and labels[i] not in hl
                cls = f"ch-bar ch-h s{min(si, 3)}" + (" muted" if muted else "") + (" hl" if labels[i] in hl else "")
                key = f' data-morph="chart-{E(cid)}-{E(labels[i])}-{si}"' if cid and spec.get("morph") else ""
                grow = "" if key or st else " ch-grow"
                bars.append(f'<div class="{cls}{grow}"{key}{st} style="left:{fmt(L)}em;top:{fmt(y)}em;width:{fmt(vx(v) - L)}em;height:{fmt(bh * 0.92)}em;--i:{i}"></div>')
                if spec.get("values", True):
                    vk = f' data-morph="chart-{E(cid)}-{E(labels[i])}-{si}-v"' if key else ""
                    bars.append(f'<span class="ch-val ch-val-h{" muted" if muted else ""}{" hl" if labels[i] in hl else ""}{grow and " ch-fade"}"{vk}{st} '
                                f'style="left:{fmt(vx(v))}em;top:{fmt(y + bh * 0.46)}em;--i:{i}">{E(num_label(v, unit))}</span>')
        for i, lab in enumerate(labels):
            htmlp.append(f'<span class="ch-cat ch-cat-y{" hl" if lab in hl else ""}" style="right:{fmt(W - L + 0.5)}em;top:{fmt(T + (i + 0.5) * slot)}em">{E(lab)}</span>')
    elif t in ("line", "area"):
        for si, s in enumerate(series):
            vals = s.get("values", [])
            pts = [(cat_x(i), vy(v)) for i, v in enumerate(vals)]
            if not pts:
                continue
            d = "M" + " L".join(f"{fmt(x)} {fmt(y)}" for x, y in pts)
            area = ""
            if t == "area" and si == 0:
                area = f'<path d="{d} L{fmt(pts[-1][0])} {fmt(T + ph)} L{fmt(pts[0][0])} {fmt(T + ph)} Z" class="ch-area"/>'
            st = step_attr(si) if spec.get("series_steps") and si > 0 else ""
            a = st or (f' data-anim="draw" data-delay="{300 + si * 250}"' if anim else "")
            if st:
                a = st + ' data-anim="draw"'
            end = pts[-1]
            dot = f'<circle cx="{fmt(end[0])}" cy="{fmt(end[1])}" r=".26" class="ch-dot s{min(si, 3)}"/>'
            svgs.append(f'<svg class="ch-svg" viewBox="0 0 {fmt(W)} {fmt(H)}" style="width:{fmt(W)}em;height:{fmt(H)}em"{a} aria-hidden="true">'
                        f'{area}<path d="{d}" class="ch-line s{min(si, 3)}"/>{dot}</svg>')
            if s.get("name"):
                htmlp.append(f'<span class="ch-end s{min(si, 3)}"{st} style="left:{fmt(end[0] + 0.5)}em;top:{fmt(end[1])}em">{E(s["name"])}'
                             + (f' <b>{E(num_label(vals[-1], unit))}</b>' if spec.get("values", True) else "") + "</span>")
        for i, lab in enumerate(labels):
            htmlp.append(f'<span class="ch-cat" style="left:{fmt(cat_x(i))}em;top:{fmt(T + ph + 0.35)}em">{E(lab)}</span>')
    elif t == "scatter":
        def sx(v):
            return L + pw * (v - xmin) / (xmax - xmin)
        for si, s in enumerate(series):
            st = step_attr(si) if spec.get("series_steps") and si > 0 else ""
            for p in s.get("points", []):
                bars.append(f'<div class="ch-pt s{min(si, 3)}{" ch-grow" if not st else ""}"{st} style="left:{fmt(sx(p[0]))}em;top:{fmt(vy(p[1]))}em"></div>')
                if len(p) > 2 and p[2]:
                    htmlp.append(f'<span class="ch-ptl"{st} style="left:{fmt(sx(p[0]) + 0.5)}em;top:{fmt(vy(p[1]))}em">{E(str(p[2]))}</span>')
        for k2 in range(ticks + 1):
            v = xmin + (xmax - xmin) * k2 / ticks
            htmlp.append(f'<span class="ch-cat" style="left:{fmt(sx(v))}em;top:{fmt(T + ph + 0.35)}em">{E(num_label(v, spec.get("xunit", "")))}</span>')
        if spec.get("xlabel"):
            htmlp.append(f'<span class="ch-axis-title" style="right:{fmt(R)}em;top:{fmt(T + ph + 1.3)}em">{E(spec["xlabel"])}</span>')

    # annotations
    ann = []
    for j, a in enumerate(spec.get("annotations", [])):
        st = step_attr(a.get("step")) if a.get("step") else (f' data-anim="fade" data-delay="{1400 + j * 300}"' if anim else "")
        kind = a.get("type", "note")
        lab = E(str(a.get("label", "")))
        if kind == "target":
            if t == "hbar":
                x = vx(float(a["value"]))
                ann.append(f'<div class="ch-ann"{st}><svg class="ch-svg" viewBox="0 0 {fmt(W)} {fmt(H)}" style="width:{fmt(W)}em;height:{fmt(H)}em" aria-hidden="true">'
                           f'<line x1="{fmt(x)}" x2="{fmt(x)}" y1="{fmt(T - 0.4)}" y2="{fmt(T + ph)}" class="ch-target"/></svg>'
                           f'<span class="ch-ann-label" style="left:{fmt(x)}em;top:{fmt(T - 0.9)}em;transform:translate(-50%,-50%)">{lab}</span></div>')
            else:
                y = vy(float(a["value"]))
                ann.append(f'<div class="ch-ann"{st}><svg class="ch-svg" viewBox="0 0 {fmt(W)} {fmt(H)}" style="width:{fmt(W)}em;height:{fmt(H)}em" aria-hidden="true">'
                           f'<line x1="{fmt(L)}" x2="{fmt(L + pw)}" y1="{fmt(y)}" y2="{fmt(y)}" class="ch-target"/></svg>'
                           f'<span class="ch-ann-label" style="right:{fmt(R)}em;top:{fmt(y - 0.75)}em">{lab}</span></div>')
        elif kind == "band":
            i0, i1 = idx(a["from"]), idx(a["to"])
            x0, x1 = L + pw * i0 / n, L + pw * (i1 + 1) / n
            ann.append(f'<div class="ch-ann"{st}><div class="ch-band" style="left:{fmt(x0)}em;top:{fmt(T)}em;width:{fmt(x1 - x0)}em;height:{fmt(ph)}em"></div>'
                       f'<span class="ch-ann-label" style="left:{fmt((x0 + x1) / 2)}em;top:{fmt(T - 0.9)}em;transform:translate(-50%,-50%)">{lab}</span></div>')
        elif kind in ("point", "note"):
            i = idx(a.get("at", 0))
            si = int(a.get("series", 0))
            if kind == "point" and t in ("bar", "line", "area"):
                v = series[si]["values"][i]
                x, y = cat_x(i), vy(v)
                if t == "bar":
                    k = len(series)
                    slot = pw / n
                    bw = slot * 0.62 / k
                    x = L + i * slot + slot * 0.19 + si * bw + bw * 0.46
                    y = y - (1.5 if spec.get("values", n <= 12) else 0.4)
            else:
                x = cat_x(i) if t != "hbar" else vx(float(a.get("value", 0)))
                y = vy(float(a.get("value", vmax)))
            dy = float(a.get("dy", -2.4))
            dx = float(a.get("dx", 0))
            ring = f'<circle cx="{fmt(x)}" cy="{fmt(y)}" r=".55" class="ch-ring"/>' if kind == "point" else ""
            ann.append(f'<div class="ch-ann"{st}><svg class="ch-svg" viewBox="0 0 {fmt(W)} {fmt(H)}" style="width:{fmt(W)}em;height:{fmt(H)}em" aria-hidden="true">'
                       f'{ring}<line x1="{fmt(x)}" y1="{fmt(y - (0.55 if ring else 0))}" x2="{fmt(x + dx)}" y2="{fmt(y + dy + 0.6)}" class="ch-leader"/></svg>'
                       f'<span class="ch-ann-label ch-callout" style="left:{fmt(x + dx)}em;top:{fmt(y + dy)}em">{lab}</span></div>')

    base = f'<svg class="ch-svg ch-bg" viewBox="0 0 {fmt(W)} {fmt(H)}" style="width:{fmt(W)}em;height:{fmt(H)}em" aria-hidden="true">{"".join(parts)}</svg>'
    legend = ""
    if t in ("bar", "hbar", "scatter") and len(series) > 1:
        legend = '<div class="ch-legend">' + "".join(
            f'<span class="s{min(i, 3)}"{step_attr(i) if spec.get("series_steps") and i > 0 else ""}>{E(s.get("name", ""))}</span>' for i, s in enumerate(series)) + "</div>"
    label = spec.get("aria", "グラフ: " + " / ".join(s.get("name", "") for s in series if s.get("name")))
    return wrap(f"mk-chart ch-type-{t}", attrs, f"--mk-font:{font}px;width:{fmt(W)}em;height:{fmt(H)}em",
                base + "".join(svgs) + "".join(bars) + "".join(htmlp) + "".join(ann) + legend, label=label)
