/* ==========================================================================
   Slide Forge — expressive effects (v1.7). Loaded BEFORE slides.js, so the DOM it
   prepares (step markers, split text, annotation layers) is seen by the core runtime.
     kinetic text   data-anim="words | mask | type | scramble"   (slam / tracking are CSS only)
     annotations    data-annotate="underline | circle | box | highlight | strike | cross | bracket"
     zoom canvas    .zoom-view > .zoom-canvas > [data-zoom]      (one click per stop)
     slider         .ba-slider[data-compare][data-stops]           (drag / sweep before ↔ after)
     code move      .code[data-codemove] > pre[data-v] …          (tokens glide between versions)
     3D             [data-3d="globe | model | shape"]            (three.js, bundled only when used)
   State that follows clicks is driven by hidden step markers (<i class="sf-mark" data-step>):
   the core runtime reveals them, this file reads which ones are in on every deck:change.
   Export (?export) shows every effect in its final state; zoom shows the overview.
   ========================================================================== */
(() => {
  "use strict";
  window.__SF_PRISTINE_STAGE = document.querySelector(".deck-stage")?.innerHTML;   // slides.js "save" restores the slides from this
  const root = document.documentElement;
  const EXPORT = new URLSearchParams(location.search).has("export");
  const REDUCED = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const NS = "http://www.w3.org/2000/svg";
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const num = (v, d = 0) => (v == null || v === "" || isNaN(+v) ? d : +v);
  const slides = $$(".deck-stage > section.slide");
  const slideOf = (el) => el.closest("section.slide");
  const rt = (el) => (el.setAttribute("data-rt", ""), el);

  // deterministic randomness (hand-drawn wobble must look the same in every render / video frame)
  const hash = (s) => { let h = 2166136261; for (const c of String(s)) { h ^= c.codePointAt(0); h = Math.imul(h, 16777619); } return h >>> 0; };
  const rng = (seed) => () => { seed = (seed + 0x6d2b79f5) | 0; let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };

  // hidden step marker: the core runtime counts it as a click and adds .is-in when reached
  function mark(host, step) {
    const i = rt(document.createElement("i"));
    i.className = "sf-mark"; i.setAttribute("aria-hidden", "true"); i.setAttribute("data-anim", "fade");
    i.setAttribute("data-step", step == null ? "" : String(step));
    host.append(i);
    return i;
  }
  const lastIn = (marks) => marks.reduce((best, m, k) => (m.classList.contains("is-in") ? k : best), -1);

  /* === 1. KINETIC TEXT: split into words / characters === */
  const seg = typeof Intl !== "undefined" && Intl.Segmenter ? new Intl.Segmenter(root.lang || "ja", { granularity: "word" }) : null;
  function split(el, unit, wrapInner) {
    let k = 0;
    const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
    const texts = []; while (walker.nextNode()) texts.push(walker.currentNode);
    texts.forEach((t) => {
      if (t.parentElement.closest("svg, .sf-mark")) return;
      const frag = document.createDocumentFragment();
      const parts = unit === "char" ? [...t.textContent]
        : seg ? [...seg.segment(t.textContent)].map((s) => s.segment) : t.textContent.split(/(\s+)/);
      parts.forEach((p) => {
        if (!p) return;
        if (/^\s+$/.test(p)) { frag.append(p); return; }
        const s = document.createElement("span");
        s.className = unit === "char" ? "sf-c" : "sf-w";
        s.style.setProperty("--k", k++);
        if (wrapInner) { const i = document.createElement("span"); i.className = "sf-wi"; i.textContent = p; s.append(i); }
        else s.textContent = p;
        frag.append(s);
      });
      t.replaceWith(frag);
    });
    el.style.setProperty("--n", k);
  }
  $$('[data-anim="words"]').forEach((el) => split(el, "word", false));
  $$('[data-anim="mask"]').forEach((el) => split(el, "word", true));
  $$('[data-anim="type"]').forEach((el) => split(el, "char", false));

  // scramble: random glyphs settle into the real text when the element comes in
  const GLYPH_CJK = "アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワン";
  const GLYPH_LAT = "ABCDEFGHJKLMNPQRSTUVWXYZ0123456789#%&*+=";
  function scramble(el) {
    const nodes = el.__texts;
    const inSlide = slideOf(el);
    if (EXPORT || REDUCED || inSlide?.classList.contains("sf-instant")) { nodes.forEach((n, k) => (n.textContent = el.__final[k])); return; }
    const delay = parseFloat(getComputedStyle(el).getPropertyValue("--delay")) || 0;
    const dur = num(el.dataset.dur, 1100);
    const R = rng(hash(el.__final.join("")));
    const total = el.__final.join("").length || 1;
    const t0 = performance.now() + delay;
    cancelAnimationFrame(el.__raf);
    el.style.opacity = "0";                                // hold until its entrance delay is over
    const tick = (now) => {
      const t = now - t0;
      if (t < 0) { el.__raf = requestAnimationFrame(tick); return; }
      el.style.opacity = "";
      let idx = 0, done = true;
      nodes.forEach((n, k) => {
        let out = "";
        for (const ch of el.__final[k]) {
          const settle = (idx++ / total) * dur * 0.75 + dur * 0.25;
          if (t >= settle || /\s/.test(ch)) out += ch;
          else { done = false; const set = /[　-鿿＀-￯]/.test(ch) ? GLYPH_CJK : GLYPH_LAT; out += set[Math.floor(R() * set.length)]; }
        }
        n.textContent = out;
      });
      if (!done) el.__raf = requestAnimationFrame(tick);
    };
    el.__raf = requestAnimationFrame(tick);
  }
  $$('[data-anim="scramble"]').forEach((el) => {
    const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
    el.__texts = []; while (walker.nextNode()) el.__texts.push(walker.currentNode);
    el.__final = el.__texts.map((n) => n.textContent);
    new MutationObserver(() => {
      const on = el.classList.contains("is-in");
      if (on && !el.__on) scramble(el);
      if (!on) { cancelAnimationFrame(el.__raf); el.style.opacity = ""; el.__texts.forEach((n, k) => (n.textContent = el.__final[k])); }
      el.__on = on;
    }).observe(el, { attributes: true, attributeFilter: ["class"] });
  });

  /* === 2. HAND-DRAWN ANNOTATIONS === */
  const ANNOT = new Set(["underline", "circle", "box", "highlight", "strike", "cross", "bracket"]);
  $$("[data-annotate]").forEach((el) => {
    const kind = ANNOT.has(el.dataset.annotate) ? el.dataset.annotate : "underline";
    const svg = rt(document.createElementNS(NS, "svg"));
    svg.setAttribute("class", `sf-annot sf-annot-${kind}`);
    svg.setAttribute("aria-hidden", "true");
    svg.setAttribute("data-anim", "draw");
    if (el.hasAttribute("data-annotate-step")) svg.setAttribute("data-step", el.getAttribute("data-annotate-step"));
    else svg.setAttribute("data-delay", el.dataset.annotateDelay ?? "900");
    if (el.dataset.annotateColor) el.style.setProperty("--annot", el.dataset.annotateColor);
    el.classList.add("sf-annotated", `sf-annotated-${kind}`);
    el.__annot = { svg, kind };
    el.append(svg);
  });
  const P = (x, y) => `${x.toFixed(1)} ${y.toFixed(1)}`;
  function annotPaths(kind, w, h, fs, R) {
    const j = (a) => (R() - 0.5) * 2 * a;                 // jitter ±a
    const o = fs * 0.28;                                   // outset around the text box
    switch (kind) {
      case "underline": {
        const y = h + fs * 0.08;
        return [`M${P(-o * 0.5 + j(3), y + j(2))} Q${P(w * 0.5, y + fs * 0.1 + j(3))} ${P(w + o * 0.5 + j(3), y - fs * 0.04 + j(2))}`,
                `M${P(w * 0.08 + j(4), y + fs * 0.2 + j(2))} Q${P(w * 0.55, y + fs * 0.26 + j(3))} ${P(w * 0.94 + j(4), y + fs * 0.16 + j(2))}`];
      }
      case "strike": {
        const y = h * 0.54;
        return [`M${P(-o * 0.4, y + j(3))} Q${P(w * 0.5, y - fs * 0.06 + j(3))} ${P(w + o * 0.4, y + j(3))}`];
      }
      case "cross":
        return [`M${P(-o * 0.3 + j(3), j(3))} L${P(w + o * 0.3 + j(3), h + j(3))}`, `M${P(w + o * 0.3 + j(3), j(3))} L${P(-o * 0.3 + j(3), h + j(3))}`];
      case "highlight": {
        const y = h * 0.56;
        return [`M${P(-fs * 0.12, y + j(2))} Q${P(w * 0.5, y + j(fs * 0.08))} ${P(w + fs * 0.12, y + j(2))}`];
      }
      case "box": {
        const q = () => [[-o + j(4), -o * 0.8 + j(3)], [w + o + j(4), -o * 0.8 + j(3)], [w + o + j(4), h + o * 0.8 + j(3)], [-o + j(4), h + o * 0.8 + j(3)]];
        const a = q(), b = q();
        const d = (c) => `M${P(...c[0])} L${P(...c[1])} L${P(...c[2])} L${P(...c[3])} Z`;
        return [d(a), d(b)];
      }
      case "bracket": {
        const t = -o * 0.7, bt = h + o * 0.7, arm = Math.min(fs * 0.5, w * 0.2);
        return [`M${P(-o + arm, t + j(2))} L${P(-o + j(2), t + j(2))} L${P(-o + j(2), bt + j(2))} L${P(-o + arm, bt + j(2))}`,
                `M${P(w + o - arm, t + j(2))} L${P(w + o + j(2), t + j(2))} L${P(w + o + j(2), bt + j(2))} L${P(w + o - arm, bt + j(2))}`];
      }
      default: {                                           // circle: one loose loop that overshoots its start
        const cx = w / 2, cy = h / 2, rx = w / 2 + fs * 0.5, ry = h / 2 + fs * 0.32;
        const a0 = -Math.PI * 0.62 + j(0.25), sweep = Math.PI * 2 + 0.45 + j(0.15), n = 28;
        const pts = [];
        for (let k = 0; k <= n; k++) {
          const a = a0 + (sweep * k) / n, wob = 1 + j(0.035) + (k / n) * 0.06;
          pts.push([cx + Math.cos(a) * rx * wob, cy + Math.sin(a) * ry * wob]);
        }
        let d = `M${P(...pts[0])}`;
        for (let k = 1; k < pts.length - 1; k++) {        // Catmull-Rom → cubic Bézier
          const p0 = pts[k - 1], p1 = pts[k], p2 = pts[k + 1], p3 = pts[Math.min(k + 2, pts.length - 1)];
          const c1 = [p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6], c2 = [p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6];
          d += ` C${P(...c1)} ${P(...c2)} ${P(...p2)}`;
        }
        return [d];
      }
    }
  }
  function drawAnnotation(el) {
    const { svg, kind } = el.__annot;
    const w = el.offsetWidth, h = el.offsetHeight;
    if (!w || !h) return;
    const fs = parseFloat(getComputedStyle(el).fontSize) || 36;
    const R = rng(hash(el.textContent + kind + (el.dataset.annotateSeed || "")));
    const pad = fs * 1.2;
    svg.setAttribute("viewBox", `${-pad} ${-pad} ${w + pad * 2} ${h + pad * 2}`);
    Object.assign(svg.style, { left: -pad + "px", top: -pad + "px", width: w + pad * 2 + "px", height: h + pad * 2 + "px" });
    const sw = kind === "highlight" ? h * 0.78 : Math.max(3, fs * 0.075);
    svg.style.setProperty("--sw", sw + "px");
    svg.innerHTML = annotPaths(kind, w, h, fs, R).map((d) => `<path d="${d}"/>`).join("");
    [...svg.children].forEach((p, k) => {
      const L = Math.ceil(p.getTotalLength()) + 2;
      p.style.strokeDasharray = L; p.style.setProperty("--len", L); p.style.strokeDashoffset = 0;
      if (k) p.style.transitionDelay = `calc(var(--delay) + ${k * 380}ms)`;
    });
  }

  /* === 3. ZOOM CANVAS (Prezi-style camera) === */
  const views = $$(".zoom-view").filter((v) => v.querySelector(".zoom-canvas"));
  views.forEach((view) => {
    const canvas = view.querySelector(".zoom-canvas");
    const stops = $$("[data-zoom]", canvas).map((el, k) => ({ el, k, o: num(el.dataset.zoom, 1000 + k) }))
      .sort((a, b) => a.o - b.o || a.k - b.k).map((x) => x.el);
    view.__canvas = canvas; view.__stops = stops;
    view.__marks = stops.map((s) => mark(canvas, s.dataset.zoomStep));
    if (view.dataset.zoomEnd === "overview") { view.__marks.push(mark(canvas, view.dataset.zoomEndStep)); view.__endOverview = true; }
  });
  function camTransform(view, idx) {
    const canvas = view.__canvas;
    const VW = view.clientWidth, VH = view.clientHeight;
    let x = 0, y = 0, w = canvas.offsetWidth, h = canvas.offsetHeight, pad = num(view.dataset.zoomPad, 0.03);
    const t = idx >= 0 ? view.__stops[idx] : null;
    if (t) {
      x = 0; y = 0;
      for (let n = t; n && n !== canvas; n = n.offsetParent) { x += n.offsetLeft; y += n.offsetTop; }
      w = t.offsetWidth; h = t.offsetHeight; pad = num(t.dataset.zoomPad, num(view.dataset.zoomPad, 0.06));
    }
    const s = Math.min(VW / (w * (1 + 2 * pad)), VH / (h * (1 + 2 * pad)));
    return { s, tx: VW / 2 - s * (x + w / 2), ty: VH / 2 - s * (y + h / 2), str: `translate(${(VW / 2 - s * (x + w / 2)).toFixed(2)}px, ${(VH / 2 - s * (y + h / 2)).toFixed(2)}px) scale(${s.toFixed(5)})` };
  }
  function camera(view, idx, instant) {
    const canvas = view.__canvas;
    const to = camTransform(view, idx);
    const from = view.__cam;
    view.__cam = to; view.__idx = idx;
    canvas.getAnimations().forEach((a) => a.cancel());
    canvas.style.transform = to.str;
    view.__stops.forEach((st, k) => { st.classList.toggle("is-focus", k === idx); st.classList.toggle("is-dim", idx >= 0 && k !== idx); });
    view.classList.toggle("is-zoomed", idx >= 0);
    if (instant || !from || from.str === to.str || REDUCED) return;
    const dur = num(view.dataset.zoomDur, 1300);
    const frames = [{ transform: from.str }];
    if (view.dataset.zoomArc !== "off" && from.s > to.s * 0.4 && to.s > from.s * 0.4 && Math.max(from.s, to.s) > 1.2 * camTransform(view, -1).s) {
      // region → region: pull back a little mid-flight so the audience keeps its bearings
      const ov = camTransform(view, -1);
      const ms = Math.max(ov.s, Math.min(from.s, to.s) * 0.55);
      const k = (ms - ov.s) / Math.max(1e-6, Math.min(from.s, to.s) - ov.s);
      const mx = ov.tx + ((from.tx + to.tx) / 2 - ov.tx) * Math.max(0, Math.min(1, k)) * (ms / Math.min(from.s, to.s));
      const my = ov.ty + ((from.ty + to.ty) / 2 - ov.ty) * Math.max(0, Math.min(1, k)) * (ms / Math.min(from.s, to.s));
      frames.push({ transform: `translate(${mx.toFixed(2)}px, ${my.toFixed(2)}px) scale(${ms.toFixed(5)})`, offset: 0.5 });
    }
    frames.push({ transform: to.str });
    canvas.animate(frames, { duration: dur, easing: "cubic-bezier(.65, 0, .35, 1)" });
  }

  /* === 4. COMPARE SLIDER (before ↔ after) === */
  const compares = $$(".ba-slider");
  compares.forEach((el) => {
    const kids = [...el.children].filter((c) => !c.matches("aside, .sf-mark"));
    (el.querySelector(".cmp-before") || kids[0])?.classList.add("cmp-before");
    (el.querySelector(".cmp-after") || kids[1])?.classList.add("cmp-after");
    el.setAttribute("data-no-nav", "");
    const handle = rt(document.createElement("div"));
    handle.className = "cmp-handle"; handle.setAttribute("aria-hidden", "true"); handle.innerHTML = "<i></i>";
    el.append(handle);
    const labels = (el.dataset.labels || "").split(",").map((s) => s.trim()).filter(Boolean);
    labels.slice(0, 2).forEach((t, k) => {
      const s = rt(document.createElement("span"));
      s.className = `cmp-label cmp-label-${k ? "after" : "before"}`; s.textContent = t; el.append(s);
    });
    el.__stops = (el.dataset.stops || "").split(",").map((s) => s.trim()).filter(Boolean).map(Number);
    el.__marks = el.__stops.map(() => mark(el));
    el.__init = num(el.dataset.compare, 50);
    el.style.setProperty("--pos", el.__init + "%");
    const setFrom = (e) => {
      const r = el.getBoundingClientRect();
      el.style.setProperty("--pos", Math.max(0, Math.min(100, ((e.clientX - r.left) / r.width) * 100)).toFixed(2) + "%");
    };
    el.addEventListener("pointerdown", (e) => { if (EXPORT) return; el.setPointerCapture(e.pointerId); el.classList.add("is-drag"); setFrom(e); e.stopPropagation(); });
    el.addEventListener("pointermove", (e) => { if (el.classList.contains("is-drag")) setFrom(e); });
    const up = () => el.classList.remove("is-drag");
    el.addEventListener("pointerup", up); el.addEventListener("pointercancel", up);
    ["click", "touchstart", "touchend"].forEach((t) => el.addEventListener(t, (e) => e.stopPropagation(), { passive: true }));
  });
  function comparePos(el, entering, instant) {
    const k = lastIn(el.__marks);
    const pos = k >= 0 ? el.__stops[k] : el.__init;
    if (entering && !instant && !REDUCED && el.dataset.sweep !== "off") {
      el.classList.add("is-drag"); el.style.setProperty("--pos", (el.dataset.sweepFrom ?? 100) + "%");
      void el.offsetWidth;
      clearTimeout(el.__t);
      el.__t = setTimeout(() => { el.classList.remove("is-drag"); el.style.setProperty("--pos", pos + "%"); }, num(el.dataset.sweepDelay, 500));
      return;
    }
    if (instant) { el.classList.add("is-drag"); el.style.setProperty("--pos", pos + "%"); void el.offsetWidth; el.classList.remove("is-drag"); }
    else el.style.setProperty("--pos", pos + "%");
  }

  /* === 5. CODE MOVE (Shiki-magic-move-style token transitions) === */
  const KW = {
    js: "const let var function return if else for while do of in new class extends import export from default async await try catch finally throw typeof instanceof interface type enum implements public private protected readonly static null undefined true false this super switch case break continue yield as void",
    py: "def return if elif else for while in import from as class with try except finally raise lambda None True False and or not is pass yield async await global nonlocal assert del break continue self",
    sql: "select from where and or not insert into values update set delete create table alter add drop index join left right inner outer full on group by order having limit offset as distinct null primary key foreign references default unique case when then else end count sum avg min max in is like between union all with",
    go: "func package import return if else for range var const type struct interface map chan go defer select case switch break continue nil true false",
    sh: "if then else fi for in do done while case esac function export echo return local",
  };
  KW.ts = KW.js; KW.jsx = KW.js; KW.tsx = KW.js; KW.python = KW.py; KW.bash = KW.sh;
  const kwSet = {}; const kwOf = (lang) => (kwSet[lang] ??= new Set((KW[lang] || KW.js).split(" ")));
  function tokenize(src, lang) {
    const cm = { py: "#[^\\n]*", python: "#[^\\n]*", sh: "#[^\\n]*", bash: "#[^\\n]*", sql: "--[^\\n]*" }[lang] || "\\/\\/[^\\n]*|\\/\\*[\\s\\S]*?\\*\\/";
    const re = new RegExp(`(${cm})|("(?:\\\\.|[^"\\\\\\n])*"|'(?:\\\\.|[^'\\\\\\n])*'|\`(?:\\\\.|[^\`\\\\])*\`)|(\\b\\d[\\d_.]*\\b)|([A-Za-z_$][\\w$]*)|(\\s+)|([^\\sA-Za-z_$\\d])`, "g");
    const kws = kwOf(lang), ci = lang === "sql";
    const out = []; let m;
    while ((m = re.exec(src))) {
      const t = m[0];
      if (m[5]) { out.push({ t, ws: true }); continue; }
      let c = m[1] ? "c" : m[2] ? "s" : m[3] ? "n" : "";
      if (m[4]) {
        if (kws.has(ci ? t.toLowerCase() : t)) c = "k";
        else if (/^\s*\(/.test(src.slice(re.lastIndex))) c = "f";
      }
      out.push({ t, c });
    }
    return out;
  }
  function lcsPairs(a, b) {                               // indices of matching non-space tokens
    const n = a.length, m = b.length, dp = new Uint16Array((n + 1) * (m + 1));
    for (let i = n - 1; i >= 0; i--) for (let j = m - 1; j >= 0; j--)
      dp[i * (m + 1) + j] = a[i].t === b[j].t ? dp[(i + 1) * (m + 1) + j + 1] + 1 : Math.max(dp[(i + 1) * (m + 1) + j], dp[i * (m + 1) + j + 1]);
    const pairs = []; let i = 0, j = 0;
    while (i < n && j < m) {
      if (a[i].t === b[j].t) { pairs.push([i, j]); i++; j++; }
      else if (dp[(i + 1) * (m + 1) + j] >= dp[i * (m + 1) + j + 1]) i++; else j++;
    }
    return pairs;
  }
  const lineSet = (spec) => {
    const s = new Set();
    String(spec || "").split(",").forEach((p) => { const [a, b] = p.split("-").map(Number); if (a) for (let k = a; k <= (b || a); k++) s.add(k); });
    return s;
  };
  let tokId = 0;
  $$("[data-codemove]").forEach((el) => {
    const lang = (el.dataset.lang || "js").toLowerCase();
    const vs = $$(":scope > pre, :scope > .cm-v", el);
    if (!vs.length) return;
    const versions = vs.map((p) => ({
      toks: tokenize(p.textContent.replace(/^\n/, "").replace(/\s+$/, ""), lang),
      hl: lineSet(p.dataset.hl), dim: p.hasAttribute("data-focus") ? lineSet(p.dataset.focus) : null, step: p.getAttribute("data-step"),
    }));
    versions.forEach((v, k) => {
      const solid = v.toks.filter((t) => !t.ws);
      if (k === 0) solid.forEach((t) => (t.id = ++tokId));
      else {
        const prev = versions[k - 1].toks.filter((t) => !t.ws);
        const map = new Map(lcsPairs(prev, solid).map(([i, j]) => [j, prev[i].id]));
        solid.forEach((t, j) => (t.id = map.get(j) ?? ++tokId));
      }
      v.lines = 1 + v.toks.reduce((a, t) => a + (t.ws ? (t.t.match(/\n/g) || []).length : 0), 0);
    });
    vs.forEach((p) => p.remove());
    [...el.childNodes].forEach((n) => { if (n.nodeType === 3 && !n.textContent.trim()) n.remove(); });   // white-space: pre would show them
    if (el.dataset.file) {
      const f = rt(document.createElement("div")); f.className = "cm-file"; f.textContent = el.dataset.file; el.append(f);
    }
    const view = rt(document.createElement("code")); view.className = "cm-view"; el.append(view);
    el.__versions = versions; el.__view = view; el.__v = -1;
    el.__marks = versions.slice(1).map((v) => mark(el, v.step));
  });
  function codeHTML(v) {
    const lines = [[]];
    v.toks.forEach((t) => {
      if (!t.ws) { lines.at(-1).push(t); return; }
      const parts = t.t.split("\n");
      parts.forEach((p, k) => { if (k) lines.push([]); if (p) lines.at(-1).push({ t: p, ws: true }); });
    });
    const esc = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    return lines.map((ln, k) => {
      const cls = ["ln", v.hl.has(k + 1) ? "hl" : "", v.dim && !v.dim.has(k + 1) ? "dim" : ""].filter(Boolean).join(" ");
      const inner = ln.map((t) => (t.ws ? esc(t.t) : `<span class="t${t.c ? " " + t.c : ""}" data-id="${t.id}">${esc(t.t)}</span>`)).join("");
      return `<span class="${cls}">${inner || "​"}</span>`;
    }).join("");
  }
  function codeShow(el, v, animate) {
    if (v === el.__v) return;
    const view = el.__view, old = new Map();
    if (animate && !REDUCED) view.querySelectorAll(".t").forEach((s) => old.set(s.dataset.id, { x: s.offsetLeft, y: s.offsetTop, node: s }));
    el.__v = v;
    view.innerHTML = codeHTML(el.__versions[v]);
    if (!old.size) return;
    const E = "cubic-bezier(.65, 0, .35, 1)", D = num(el.dataset.dur, 750);
    view.querySelectorAll(".t").forEach((s) => {
      const o = old.get(s.dataset.id);
      if (o) {
        old.delete(s.dataset.id);
        const dx = o.x - s.offsetLeft, dy = o.y - s.offsetTop;
        if (dx || dy) s.animate([{ transform: `translate(${dx}px, ${dy}px)` }, { transform: "none" }], { duration: D, easing: E });
      } else s.animate([{ opacity: 0, transform: "translateY(.35em)" }, { opacity: 0, offset: 0.4 }, { opacity: 1, transform: "none" }], { duration: D + 150, easing: "ease-out" });
    });
    view.querySelectorAll(".ln.hl").forEach((l) => l.animate([{ backgroundColor: "transparent" }, { backgroundColor: "transparent", offset: 0.5 }, {}], { duration: D + 200 }));
    old.forEach((o) => {
      const g = o.node.cloneNode(true);
      g.classList.add("cm-ghost"); g.style.left = o.x + "px"; g.style.top = o.y + "px";
      view.append(g);
      g.animate([{ opacity: 1 }, { opacity: 0, transform: "translateY(-.3em)" }], { duration: D * 0.45, easing: "ease-in", fill: "forwards" }).finished.then(() => g.remove());
    });
  }
  function codeLayout(el) {                                // reserve the tallest version's height: no jumps
    const view = el.__view, cur = el.__v;
    const lh = parseFloat(getComputedStyle(view).lineHeight) || 48;
    const lines = Math.max(...el.__versions.map((v) => v.lines));
    view.style.minHeight = (lines * lh).toFixed(1) + "px";
    if (cur < 0) codeShow(el, 0, false);
  }

  /* === 6. 3D (three.js) === */
  const LAND = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAADA/wAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAPj/z////3EAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAD/++f///wcAAPADgAEAAOADAAAAAAAAAAAAAAAg3N4f/v///wcAAB8AAAAAAAA4AAAAAAAAAAAAAAADAOAH/P///wcAAA4AAAAAAAAwAAAAAAAAAAAAAAC8cQwBAP///wcAAAAAAIAHAMD/DwDwAAAAAAAAAOAAAAAAAPz//wMAAAAAAGAAAPz/AQAAAAAAAAAAAOBdc/MDAPj//wEAAAAAABjAwP///z9gAAAAA4AAAED8A/P/AOD//wEAAAAAADjg/v///z//HwCAAPj/A0/8X4PwB/D//wAAAOA/AADh/v///////wM+A/7///8Pw56BB+D/DwAAAPz/Y+zf/f//////////N/D///////+Bf/D/AQAAAP7/x////v//////////GP7//////7/wJ+AfAH4AAD9++P//////////////AOD//////88GH8AfAAwAwJ////////////////9/APz//////wNxDIAPAAAA8M///////////////98/APzf/////wHwAwAGAAAA+M///////////////+ADAPAB+P///wHwMwAAAAAA8A//////////////ZBgAAIACgP///wPgfwAAAAAQAAf///////////8fAA4AACAAAP///z/gfwAAAAAwYMf///////////8PAB8AAAQAAP7////5/wMAAABoQOj///////////8DAA8AAAAAgPz////5/wcAAADs+P////////////9/AAcAAAAAAPj////7/wMAAADg+f////////////9/AAEAAAAAAPj/////zwAAAAAw/v////////////+/AAAAAAAAAPD/////Gw4AAACg//////////////8fAAAAAAAAAOD/////HxAAAADA//////////////8fAAAAAAAAAOD//////wAAAACA//9P/vj///////8PAAAAAAAAAOD/////EwAAAACA//wHfPz////////HAAAAAAAAAOD/////AQAAAAD8g/EH8Pj////////gAAAAAAAAAOD/////AAAAAAD8Aebn+fH//////z8AAAAAAAAAAOD///9/AAAAAAD8AGT8//H//////xpgAAAAAAAAAMD///8/AAAAAAD8AMT8//H/////fzggAAAAAAAAAID///8fAAAAAABwdAD8/////////zE4AAAAAAAAAID///8fAAAAAACwfwBD/////////zA/AAAAAAAAAAD+//8PAAAAAAD4fwAA/////////wAHAAAAAAAAAAD8//8DAAAAAAD8/2OA/////////4EAAAAAAAAAAADo//8DAAAAAAD8/+///////////wEAAAAAAAAAAADo/wkCAAAAAAD+//////z//////wEAAAAAAAAAAADYfwACAAAAAID///8///n//////wEAAAAAAAAAAACgfwAWAAAAAMD///9//+H//////wAAAAAAAAAAAAAgfwAAAAAAAMD///9//jPg////fwAAAAAAAAAAAAAAfgAAAAAAAOD//////H/A////PwEAAAAAAAAAAAAAfAAIAAAAAOD//////f/A/+f/BwAAAAAAAAAAAAAAfDBwAAAAAOD/////+X8A/sN/AAAAAAAAAAAAAAAA+DgAAwAAAOD/////+T8A/oB/AwAAAAAAAAAAAAAA4B8AAAAAAOD/////8x8AfoB/AAMAAAAAAAAAAAAAgPwAAAAAAOD/////8wcAPoD+AAEAAAAAAAAAAAAAAPgBAAAAAOD/////7wEAHAD+AQEAAAAAAAAAAAAAAMAAAAAAAOD/////PwAAHAD8AQQAAAAAAAAAAAAAAICAAgAAAMD/////HwMAGADgAAoAAAAAAAAAAAAAAADBfgAAAID//////wMAGABAAAAAAAAAAAAAAAAAAADy/wAAAID//////wEAIAAGAAwAAAAAAAAAAAAAAADw/wEAAAD//////wEAIAAIAAgAAAAAAAAAAAAAAADw/x8AAAD8+P///wAAAAAZYAAAAAAAAAAAAAAAAADg/z8AAAAAwP///wAAAAAbMAAAAAAAAAAAAAAAAADw/z8AAAAAwP//fwAAAAAWfAAAAAAAAAAAAAAAAAD4/38AAAAAwP//HwAAAAAcficAAAAAAAAAAAAAAAD8//8BAAAAwP//DwAAAAAYPiABAAAAAAAAAAAAAAD8//8DAAAAwP//BwAAAAA4vgEaAAAAAAAAAAAAAAD8//8/AAAAgP//BwAAAABwEBL+AAAAAAAAAAAAAAD8////AAAAAP//AwAAAABgAADwAQAAAAAAAAAAAAD8////AQAAAP//AwAAAADABADyAwEAAAAAAAAAAAD4////AQAAAP7/AwAAAAAAHADwBgQAAAAAAAAAAADw////AAAAAP7/BwAAAAAAAAQADAAAAAAAAAAAAADw//9/AAAAAP7/BwAAAAAAAAAAAAAAAAAAAAAAAADg//9/AAAAAP7/BwAAAAAAAICHAAAAAAAAAAAAAADg//8/AAAAAP//BwEAAAAAANDHAAAAAAAAAAAAAADA//8/AAAAAP//hwMAAAAAAPjHAQAAAAAAAAAAAAAA//8/AAAAAP//4QEAAAAAAPzfAQAAAAAAAAAAAAAA/v8/AAAAAP//4AEAAAAAAP7/AwAAAAAAAAAAAAAA/v8fAAAAAP5/wAAAAAAAgP//ByAAAAAAAAAAAAAA/v8fAAAAAP7/4AAAAAAA4P//D0AAAAAAAAAAAAAA/v8HAAAAAPz/4AAAAAAA8P//HwAAAAAAAAAAAAAA/v8AAAAAAPx/YAAAAAAA8P//PwAAAAAAAAAAAAAA/v8AAAAAAPw/AAAAAAAA8P//PwAAAAAAAAAAAAAA/v8AAAAAAPw/AAAAAAAA8P//PwAAAAAAAAAAAAAA/38AAAAAAPgfAAAAAAAA4P//PwAAAAAAAAAAAAAA/z8AAAAAAPAPAAAAAAAA4P//PwAAAAAAAAAAAAAA/x8AAAAAAPAHAAAAAAAA4B/+PwAAAAAAAAAAAAAA/w8AAAAAAPABAAAAAAAA4Af0HwAAAAAAAAAAAAAA/wMAAAAAAAAAAAAAAAAAAADwDwAIAAAAAAAAAACA/wMAAAAAAAAAAAAAAAAAAADgDwAQAAAAAAAAAACA/wEAAAAAAAAAAAAAAAAAAADAAgBwAAAAAAAAAACAfwAAAAAAAAAAAAAAAAAAAAAAAAAwAAAAAAAAAACAHwAAAAAAAAAAAAAAAAAAAAAABgAQAAAAAAAAAACAHwAAAAAAAAAAAAAAAAAAAAAABgAMAAAAAAAAAADADwAAAAAAAAAAAAAAAAAAAAAAAAADAAAAAAAAAADABwAAAAAAAAAAAAAAAAAAAAAAAIADAAAAAAAAAADADwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAADABwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAADAAwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAADAgwEAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACABwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAHwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAMAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAGAAAAAAAAAAAADwAAAR4Pv4HAAAAAAAAAAAAAAAACAAAAAAAAAAA4P8/4P//////BwAAAAAAAAAAAAAAPwAAAAAAAADg//8//P///////wMAAAAAAAAAAACAewAAAADI/v////8///////////8BAAAAAAAAABAAeAAAAID///////////////////8DAAAAAAAe4P//fwAAAMD//////////////////38AAADA////////BwAAAPz//////////////////x8AAEDz//////8/AAAA8P///////////////////x8AABj///////8PAIAH/////////////////////38AAADA//////8/gPAD4P///////////////////wcAAAD+////////P4Dx/////////////////////w8AAAD8//////////////////////////////////8A/wMA/v//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////";                            // 240×120 land bitmap (Natural Earth 1:110m, public domain)
  let landBits = null;
  const isLand = (lat, lon) => {
    landBits ??= Uint8Array.from(atob(LAND), (c) => c.charCodeAt(0));
    const i = Math.min(239, Math.floor(((lon + 180) / 360) * 240)), j = Math.min(119, Math.floor(((90 - lat) / 180) * 120));
    const k = j * 240 + i;
    return (landBits[k >> 3] >> (k & 7)) & 1;
  };
  function cssColor(el, v, fallback) {
    const probe = document.createElement("i"); probe.style.color = `var(${v}, ${fallback})`; el.append(probe);
    const c = getComputedStyle(probe).color; probe.remove();
    const m = c.match(/-?[\d.]+/g) || [0, 0, 0];
    const f = /^color\(/.test(c) ? 255 : 1;
    return [+m[0] * f, +m[1] * f, +m[2] * f].map((x) => Math.round(Math.max(0, Math.min(255, x))));
  }
  const three = $$("[data-3d]");
  function json(s, d) { try { return s ? JSON.parse(s) : d; } catch (e) { console.warn("slide-forge 3d: bad JSON", s); return d; } }
  function init3d(el) {
    if (el.__3d) return el.__3d;
    const SF3 = window.SF3;
    if (!SF3) { el.classList.add("sf-3d-fail"); return (el.__3d = { fail: true }); }
    const { THREE } = SF3;
    const W = el.clientWidth || 800, H = el.clientHeight || 600;
    let renderer;
    try { renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, preserveDrawingBuffer: true }); }
    catch (e) { el.classList.add("sf-3d-fail"); return (el.__3d = { fail: true }); }
    renderer.setPixelRatio(Math.min(2, window.devicePixelRatio || 1));
    renderer.setSize(W, H, false);
    const cv = rt(renderer.domElement); cv.className = "sf-3d-canvas"; cv.setAttribute("aria-hidden", "true");
    el.prepend(cv);
    const col = (v, fb) => new THREE.Color().setRGB(...cssColor(el, v, fb).map((x) => x / 255), THREE.SRGBColorSpace);
    const C = { accent: col("--accent", "#e0452b"), fg: col("--fg", "#222"), muted: col("--muted", "#888"), surface: col("--surface", "#fff"), bg: col("--bg", "#fff"), accent2: col("--accent-2", "#2b59e0") };
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(num(el.dataset.fov, 30), W / H, 0.1, 100);
    camera.position.set(0, 0, num(el.dataset.distance, 4.4));
    const state = { renderer, scene, camera, C, THREE, t: 0, update: [], labels: [], el, ready: true };
    const kind = el.dataset["3d"];
    if (kind === "globe") buildGlobe(state);
    else if (kind === "model") buildModel(state);
    else buildShape(state);
    return (el.__3d = state);
  }
  function dotTexture(THREE) {
    const c = document.createElement("canvas"); c.width = c.height = 64;
    const g = c.getContext("2d"); g.fillStyle = "#fff"; g.beginPath(); g.arc(32, 32, 28, 0, Math.PI * 2); g.fill();
    const t = new THREE.CanvasTexture(c); return t;
  }
  function glowTexture(THREE, rgb) {
    const c = document.createElement("canvas"); c.width = c.height = 256;
    const g = c.getContext("2d"), gr = g.createRadialGradient(128, 128, 60, 128, 128, 128);
    gr.addColorStop(0, `rgba(${rgb},0.0)`); gr.addColorStop(0.72, `rgba(${rgb},0.28)`); gr.addColorStop(1, `rgba(${rgb},0)`);
    g.fillStyle = gr; g.fillRect(0, 0, 256, 256);
    return new THREE.CanvasTexture(c);
  }
  const ll = (THREE, lat, lon, r = 1) => {
    const phi = ((90 - lat) * Math.PI) / 180, th = ((lon + 180) * Math.PI) / 180;
    return new THREE.Vector3(-r * Math.sin(phi) * Math.cos(th), r * Math.cos(phi), r * Math.sin(phi) * Math.sin(th));
  };
  function buildGlobe(S) {
    const { THREE, scene, C, el } = S;
    const tilt = new THREE.Group(), spin = new THREE.Group();
    scene.add(tilt); tilt.add(spin);
    spin.add(new THREE.Mesh(new THREE.SphereGeometry(0.992, 64, 48), new THREE.MeshBasicMaterial({ color: C.surface, transparent: true, opacity: 0.96 })));
    const glow = new THREE.Sprite(new THREE.SpriteMaterial({ map: glowTexture(THREE, cssColor(el, "--accent", "#e0452b").join(",")), transparent: true, depthWrite: false }));
    glow.scale.set(2.36, 2.36, 1); scene.add(glow);
    const N = num(el.dataset.dots, 14000), pos = [];
    const golden = Math.PI * (3 - Math.sqrt(5));
    for (let i = 0; i < N; i++) {
      const y = 1 - ((i + 0.5) / N) * 2, lat = (Math.asin(y) * 180) / Math.PI;
      const lon = ((((i * golden * 180) / Math.PI) % 360) + 360) % 360 - 180;
      if (isLand(lat, lon)) { const v = ll(THREE, lat, lon, 1.001); pos.push(v.x, v.y, v.z); }
    }
    const g = new THREE.BufferGeometry(); g.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
    spin.add(new THREE.Points(g, new THREE.PointsMaterial({ color: C.muted, size: num(el.dataset.dotSize, 0.02), map: dotTexture(THREE), transparent: true, alphaTest: 0.4, opacity: 0.9 })));
    const points = json(el.dataset.points, []);
    const vecs = points.map((p) => ll(THREE, p[0], p[1], 1.004));
    points.forEach((p, k) => {
      const v = vecs[k];
      const dot = new THREE.Mesh(new THREE.SphereGeometry(0.022, 16, 12), new THREE.MeshBasicMaterial({ color: C.accent }));
      dot.position.copy(v); spin.add(dot);
      const ring = new THREE.Mesh(new THREE.RingGeometry(0.03, 0.04, 40), new THREE.MeshBasicMaterial({ color: C.accent, transparent: true, side: THREE.DoubleSide, depthWrite: false }));
      ring.position.copy(v.clone().multiplyScalar(1.002)); ring.lookAt(v.clone().multiplyScalar(2)); spin.add(ring);
      S.update.push((t) => { const f = ((t * 0.6 + k * 0.37) % 1); ring.scale.setScalar(1 + f * 2.4); ring.material.opacity = 0.9 * (1 - f); });
      if (p[2]) {
        const lab = rt(document.createElement("span")); lab.className = "sf-3d-label"; lab.textContent = p[2]; el.append(lab);
        S.labels.push({ lab, obj: dot });
      }
    });
    json(el.dataset.arcs, []).forEach(([a, b], k) => {
      const A = vecs[a]?.clone().normalize(), B = vecs[b]?.clone().normalize();
      if (!A || !B) return;
      const ang = A.angleTo(B), lift = 0.08 + ang * 0.28, pts = [];
      for (let i = 0; i <= 64; i++) {
        const t = i / 64, v = new THREE.Vector3().copy(A).multiplyScalar(Math.sin((1 - t) * ang)).add(B.clone().multiplyScalar(Math.sin(t * ang))).divideScalar(Math.sin(ang) || 1);
        pts.push(v.normalize().multiplyScalar(1.004 + lift * Math.sin(Math.PI * t)));
      }
      const curve = new THREE.CatmullRomCurve3(pts);
      const tube = new THREE.TubeGeometry(curve, 96, 0.0055, 6, false);
      const mesh = new THREE.Mesh(tube, new THREE.MeshBasicMaterial({ color: C.accent, transparent: true, opacity: 0.85 }));
      spin.add(mesh);
      const count = tube.index.count, per = 6 * 6;
      const pulse = new THREE.Mesh(new THREE.SphereGeometry(0.016, 12, 10), new THREE.MeshBasicMaterial({ color: C.accent }));
      spin.add(pulse);
      S.update.push((t, fin) => {
        const grow = fin ? 1 : Math.min(1, Math.max(0, (t - 0.6 - k * 0.25) / 1.4));
        tube.setDrawRange(0, Math.floor((count * grow) / per) * per);
        pulse.visible = grow >= 1 && !fin;
        if (pulse.visible) pulse.position.copy(curve.getPointAt(((t * 0.35 + k * 0.21) % 1)));
      });
    });
    const [flat, flon] = String(el.dataset.focus || "30,135").split(",").map(Number);
    const f = ll(THREE, flat, flon);
    const beta = Math.atan2(f.x, f.z);
    tilt.rotation.x = ((flat * Math.PI) / 180) * 0.85;
    S.update.push((t, fin) => { spin.rotation.y = -beta + (fin || el.dataset.spin === "off" ? 0 : Math.sin(t * 0.25) * 0.35); });
  }
  function light(S) {
    const { THREE, scene, C } = S;
    scene.add(new THREE.HemisphereLight(0xffffff, C.bg.clone().lerp(new THREE.Color(0x000000), 0.4), 1.6));
    const d = new THREE.DirectionalLight(0xffffff, 2.2); d.position.set(3, 4, 5); scene.add(d);
    const r = new THREE.DirectionalLight(C.accent, 1.2); r.position.set(-4, -1, -3); scene.add(r);
  }
  function spinUpdate(S, obj) {
    const el = S.el, speed = num(el.dataset.spin, 0.35), yaw = (num(el.dataset.yaw, -25) * Math.PI) / 180, pitch = (num(el.dataset.pitch, 12) * Math.PI) / 180;
    obj.rotation.x = pitch;
    S.update.push((t, fin) => { obj.rotation.y = yaw + (fin || isNaN(speed) ? 0 : t * speed); });
  }
  function buildShape(S) {
    const { THREE, scene, C, el } = S;
    light(S);
    const kind = el.dataset.shape || "knot";
    const geo = kind === "ico" ? new THREE.IcosahedronGeometry(1.05, 1) : kind === "torus" ? new THREE.TorusGeometry(0.85, 0.32, 48, 120)
      : kind === "sphere" ? new THREE.SphereGeometry(1, 64, 48) : new THREE.TorusKnotGeometry(0.72, 0.24, 220, 32);
    const grp = new THREE.Group();
    grp.add(new THREE.Mesh(geo, new THREE.MeshStandardMaterial({ color: C.accent, metalness: 0.35, roughness: 0.32, flatShading: kind === "ico" })));
    if (el.dataset.wire !== "off") grp.add(new THREE.LineSegments(new THREE.WireframeGeometry(kind === "ico" ? geo : new THREE.IcosahedronGeometry(1.35, 2)),
      new THREE.LineBasicMaterial({ color: C.fg, transparent: true, opacity: kind === "ico" ? 0.35 : 0.12 })));
    scene.add(grp); spinUpdate(S, grp);
  }
  function buildModel(S) {
    const { THREE, scene, C, el } = S;
    light(S);
    const src = el.dataset.src;
    S.ready = false;
    if (!src || !window.SF3.GLTFLoader) { el.classList.add("sf-3d-fail"); return; }
    new window.SF3.GLTFLoader().load(src, (gltf) => {
      const obj = gltf.scene;
      const box = new THREE.Box3().setFromObject(obj), size = box.getSize(new THREE.Vector3()), c = box.getCenter(new THREE.Vector3());
      const s = num(el.dataset.scale, 2.1) / Math.max(size.x, size.y, size.z || 1);
      obj.position.sub(c); const grp = new THREE.Group(); grp.add(obj); grp.scale.setScalar(s);
      if (el.dataset.tint) {
        const tint = el.dataset.tint === "accent" ? C.accent : new THREE.Color(el.dataset.tint);
        obj.traverse((o) => { if (o.isMesh) o.material = new THREE.MeshStandardMaterial({ color: tint, metalness: 0.25, roughness: 0.4, flatShading: true }); });
      }
      scene.add(grp); spinUpdate(S, grp);
      S.ready = true; frame3d(S, S.t, !el.__running);
    }, undefined, (err) => { console.warn("slide-forge 3d: model failed to load", err); el.classList.add("sf-3d-fail"); });
  }
  function frame3d(S, t, fin) {
    if (!S || S.fail || !S.ready) return;
    S.update.forEach((u) => u(t, fin));
    S.renderer.render(S.scene, S.camera);
    if (S.labels.length) {
      const W = S.el.clientWidth, H = S.el.clientHeight, v = new S.THREE.Vector3(), n = new S.THREE.Vector3(), cam = S.camera.position;
      S.labels.forEach(({ lab, obj }) => {
        obj.getWorldPosition(v); n.copy(v).normalize();
        const facing = n.dot(cam.clone().sub(v).normalize());
        v.project(S.camera);
        lab.style.left = ((v.x + 1) / 2) * W + "px"; lab.style.top = ((1 - v.y) / 2) * H + "px";
        lab.classList.toggle("is-back", facing < 0.2);
      });
    }
  }
  function start3d(el) {
    const S = init3d(el);
    if (S.fail || el.__running) return;
    if (EXPORT || REDUCED) { S.t = 3; frame3d(S, 3, true); return; }
    el.__running = true;
    const t0 = performance.now() - (S.t || 0) * 1000;
    const loop = (now) => { if (!el.__running) return; S.t = (now - t0) / 1000; frame3d(S, S.t, false); el.__raf = requestAnimationFrame(loop); };
    el.__raf = requestAnimationFrame(loop);
  }
  function stop3d(el) { el.__running = false; cancelAnimationFrame(el.__raf); if (el.__3d) el.__3d.t = 0; }

  /* === WIRING === */
  function maskLines(el) {                               // mask reveal goes line by line
    let top = null, line = -1;
    el.querySelectorAll(".sf-w").forEach((w) => {
      const t = w.offsetTop;
      if (top === null || Math.abs(t - top) > 4) { line++; top = t; }
      w.style.setProperty("--line", line);
    });
  }
  // tiles whose fill depends on data: pick near-black or white ink, whichever reads better
  const rgbOf = (c) => { const m = c.match(/-?[\d.]+/g) || [0, 0, 0]; const f = /^color\(/.test(c) ? 255 : 1; return [+m[0] * f, +m[1] * f, +m[2] * f]; };
  const lumOf = ([r, g, b]) => { const t = (v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; }; return 0.2126 * t(r) + 0.7152 * t(g) + 0.0722 * t(b); };
  function autoInk(el) {
    const L = lumOf(rgbOf(getComputedStyle(el).backgroundColor));
    el.style.color = (1.05 / (L + 0.05)) >= ((L + 0.05) / 0.0625) ? "#fff" : "#15161a";
  }
  function layout() {
    $$(".jp-v").forEach(autoInk);
    $$('[data-anim="mask"]').forEach(maskLines);
    $$("[data-annotate]").forEach((el) => el.__annot && drawAnnotation(el));
    $$("[data-codemove]").forEach((el) => el.__view && codeLayout(el));
    if (EXPORT) {                                          // final state for print / PDF / check.py
      views.forEach((v) => camera(v, v.dataset.zoomExport === "last" ? v.__stops.length - 1 : -1, true));
      compares.forEach((el) => el.style.setProperty("--pos", (el.__stops.length ? el.__stops.at(-1) : el.__init) + "%"));
      $$("[data-codemove]").forEach((el) => el.__view && codeShow(el, el.__versions.length - 1, false));
      three.forEach(start3d);
    }
  }
  document.addEventListener("deck:layout", layout);

  let lastSlide = -1;
  document.addEventListener("deck:change", (e) => {
    const i = e.detail.index, slide = slides[i];
    if (!slide) return;
    const entering = i !== lastSlide;
    const instant = slide.classList.contains("sf-instant");
    lastSlide = i;
    views.forEach((v) => {
      if (slideOf(v) !== slide) return;
      const k = lastIn(v.__marks);
      const idx = v.__endOverview && k === v.__marks.length - 1 ? -1 : k;
      camera(v, idx, entering || instant);
    });
    compares.forEach((el) => { if (slideOf(el) === slide) comparePos(el, entering && e.detail.step === 0, instant); });
    $$("[data-codemove]", slide).forEach((el) => el.__view && codeShow(el, Math.max(0, lastIn(el.__marks) + 1), !(entering || instant)));
    three.forEach((el) => (slideOf(el) === slide ? start3d(el) : stop3d(el)));
  });
})();
