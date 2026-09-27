/* ==========================================================================
   Slide Forge runtime — core JS (zero dependencies)
   Modes (query string):  (none)=show · ?export (all slides stacked, final state)
                          ?embed (iframe preview, no UI) · ?presenter (speaker view)
   Public API: window.deck  (used by scripts/check.py and scripts/record.py)
   ========================================================================== */
(() => {
  "use strict";
  const PRISTINE = document.documentElement.outerHTML;           // for clean "save" after inline edits
  const cfg = Object.assign({
    transition: "fade",   // fade | slide | rise | zoom | wipe | morph | none
    footer: "", chrome: true, lang: document.documentElement.lang || "ja",
    baseDelay: 140,       // ms before the first entrance animation on a slide
    autoGap: 110,         // ms between auto-sequenced entrance animations
    staggerGap: 90,       // ms between children of a data-stagger container
    countDur: 1600,       // ms for data-count number roll-ups
  }, window.DECK_CONFIG || {});

  const qs = new URLSearchParams(location.search);
  const MODE = qs.has("export") ? "export" : qs.has("presenter") ? "presenter" : qs.has("embed") ? "embed" : "show";
  const REDUCED = matchMedia("(prefers-reduced-motion: reduce)").matches || qs.has("nomotion");
  const root = document.documentElement;
  const stage = document.querySelector(".deck-stage");
  const viewport = document.querySelector(".deck-viewport");
  if (!stage) { console.error("[slide-forge] .deck-stage not found"); return; }
  const slides = [...stage.querySelectorAll(":scope > section.slide")];
  const N = slides.length;
  const JA = /^ja/.test(cfg.lang);
  const T = (ja, en) => (JA ? ja : en);
  let cur = 0, step = 0, vtRunning = null, presenterWin = null;

  const raf2 = () => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
  const num = (v, d = 0) => (v == null || v === "" || isNaN(+v) ? d : +v);

  /* === PREPARE each slide once === */
  slides.forEach((slide, i) => {
    slide.dataset.index = i;
    if (!slide.lang && cfg.lang) slide.lang = cfg.lang;

    // data-stagger="up" on a container → children inherit the anim with staggered timing
    slide.querySelectorAll("[data-stagger]").forEach((box) => {
      const kind = box.dataset.stagger || "up";
      [...box.children].forEach((c) => {
        if (c.matches("aside.notes")) return;
        if (!c.hasAttribute("data-anim")) c.setAttribute("data-anim", kind);
        c.__staggered = num(box.dataset.staggerGap, cfg.staggerGap);
      });
    });

    // steps: data-step (optionally numbered) → grouped fragments revealed by "next"
    const stepEls = [...slide.querySelectorAll("[data-step]")];
    const groups = new Map();
    stepEls.forEach((el, k) => {
      if (!el.hasAttribute("data-anim")) el.setAttribute("data-anim", "up");
      const key = el.dataset.step === "" ? 1000 + k : num(el.dataset.step, 1000 + k);
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(el);
    });
    slide.__steps = [...groups.keys()].sort((a, b) => a - b).map((k) => groups.get(k));

    // chars: split text into spans for per-character reveals (keep for short lines only)
    slide.querySelectorAll('[data-anim="chars"]').forEach((el) => {
      let k = 0;
      const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
      const texts = []; while (walker.nextNode()) texts.push(walker.currentNode);
      texts.forEach((t) => {
        const frag = document.createDocumentFragment();
        for (const ch of t.textContent) {
          if (/\s/.test(ch)) { frag.append(ch); continue; }
          const s = document.createElement("span"); s.className = "ch"; s.textContent = ch;
          s.style.transitionDelay = `calc(var(--delay) + ${k++ * num(el.dataset.charGap, 32)}ms)`;
          frag.append(s);
        }
        t.replaceWith(frag);
      });
    });

    // draw: measure SVG strokes
    slide.querySelectorAll('[data-anim="draw"]').forEach((el) => {
      el.querySelectorAll("path, line, polyline, circle, rect, polygon").forEach((s) => {
        try { const L = Math.ceil(s.getTotalLength()) + 2; s.style.strokeDasharray = L; s.style.setProperty("--len", L); s.style.strokeDashoffset = 0; } catch (e) {}
      });
    });

    // durations
    slide.querySelectorAll("[data-anim][data-dur]").forEach((el) => el.style.setProperty("--d", el.dataset.dur + "ms"));
    // data-bar-delay on bars for cascading fills
    slide.querySelectorAll(".bars, .cols-chart").forEach((box) =>
      [...box.children].forEach((b, k) => b.querySelector(".fill")?.style.setProperty("--bar-delay", 250 + k * 110 + "ms")));
    slide.querySelectorAll(".flow").forEach((f) =>
      [...f.querySelectorAll(".arrow")].forEach((a, k) => a.style.setProperty("--delay", 400 + k * 260 + "ms")));
  });

  /* === COUNTERS: data-count rolls numbers up from 0 === */
  function parseCount(el) {
    if (el.__count) return el.__count;
    const txt = el.textContent;
    const m = txt.match(/-?[\d,]*\.?\d+/);
    const target = el.dataset.count ? +el.dataset.count : m ? +m[0].replace(/,/g, "") : 0;
    const dec = (el.dataset.count || (m ? m[0] : "")).split(".")[1]?.length || 0;
    const comma = m ? m[0].includes(",") : false;
    const [pre, post] = m ? [txt.slice(0, m.index), txt.slice(m.index + m[0].length)] : ["", ""];
    return (el.__count = { target, dec, comma, pre, post, from: num(el.dataset.countFrom, 0) });
  }
  const fmt = (c, v) => c.pre + (c.comma ? v.toLocaleString("en-US", { minimumFractionDigits: c.dec, maximumFractionDigits: c.dec }) : v.toFixed(c.dec)) + c.post;
  function setCountText(el, v) {
    const c = parseCount(el);
    // keep .unit and other child markup: only rewrite the first text node that holds the number
    const tn = [...el.childNodes].find((n) => n.nodeType === 3 && /\d/.test(n.textContent));
    if (tn) {
      const m = tn.textContent.match(/-?[\d,]*\.?\d+/);
      const s = c.comma ? v.toLocaleString("en-US", { minimumFractionDigits: c.dec, maximumFractionDigits: c.dec }) : v.toFixed(c.dec);
      tn.textContent = tn.textContent.slice(0, m.index) + s + tn.textContent.slice(m.index + m[0].length);
      tn.__orig ??= m;
    } else el.textContent = fmt(c, v);
  }
  function runCount(el, delay) {
    const c = parseCount(el);
    cancelAnimationFrame(el.__raf); clearTimeout(el.__to);
    if (REDUCED || MODE !== "show") return setCountText(el, c.target);
    setCountText(el, c.from);
    const dur = num(el.dataset.countDur, cfg.countDur);
    el.__to = setTimeout(() => {
      const t0 = performance.now();
      const tick = (t) => {
        const p = Math.min(1, (t - t0) / dur), e = p === 1 ? 1 : 1 - Math.pow(2, -10 * p);
        setCountText(el, c.from + (c.target - c.from) * e);
        if (p < 1) el.__raf = requestAnimationFrame(tick);
      };
      el.__raf = requestAnimationFrame(tick);
    }, delay);
  }
  const finishCount = (el) => { cancelAnimationFrame(el.__raf); clearTimeout(el.__to); setCountText(el, parseCount(el).target); };

  /* === SLIDE STATE === */
  const inStep = (el, slide) => { const s = el.closest("[data-step]"); return s && slide.contains(s) ? s : null; };

  function entrance(slide, instant) {
    // entrance group: data-anim elements not governed by a step
    const els = [...slide.querySelectorAll("[data-anim]")].filter((el) => !inStep(el, slide));
    const auto = slide.dataset.auto !== "off";
    let t = cfg.baseDelay;
    els.forEach((el) => {
      let d;
      if (el.dataset.delay != null) d = cfg.baseDelay + num(el.dataset.delay);
      else if (!auto) d = cfg.baseDelay;
      else { d = t; t += el.__staggered || cfg.autoGap; }
      el.style.setProperty("--delay", (instant ? 0 : d) + "ms");
      el.__delay = d;
      el.classList.add("is-in");
    });
    slide.querySelectorAll("[data-count]").forEach((el) => {
      if (inStep(el, slide)) return;
      const host = el.closest("[data-anim]");
      instant ? finishCount(el) : runCount(el, (host?.__delay ?? cfg.baseDelay) + 120);
    });
  }

  function revealStep(slide, k, instant) {
    const group = slide.__steps[k] || [];
    let t = 0;
    group.forEach((el) => {
      [el, ...el.querySelectorAll("[data-anim]")].forEach((a) => {
        const d = a.dataset.delay != null ? num(a.dataset.delay) : t;
        if (a.dataset.delay == null) t += a.__staggered || 80;
        a.style.setProperty("--delay", (instant ? 0 : d) + "ms"); a.__delay = d; a.classList.add("is-in");
      });
      el.querySelectorAll("[data-count]").forEach((c) => (instant ? finishCount(c) : runCount(c, 150)));
      if (el.matches("[data-count]")) instant ? finishCount(el) : runCount(el, 150);
    });
  }
  function hideStep(slide, k) {
    (slide.__steps[k] || []).forEach((el) =>
      [el, ...el.querySelectorAll("[data-anim]")].forEach((a) => { a.style.setProperty("--delay", "0ms"); a.classList.remove("is-in", "is-past"); }));
  }
  function markPast(slide, s) {
    slide.__steps.forEach((g, k) => g.forEach((el) => el.classList.toggle("is-past", k < s - 1)));
  }

  function resetSlide(slide) {
    slide.classList.remove("is-played");
    slide.querySelectorAll(".is-in").forEach((el) => el.classList.remove("is-in", "is-past"));
    slide.querySelectorAll("[data-count]").forEach((el) => { cancelAnimationFrame(el.__raf); clearTimeout(el.__to); });
  }

  function activate(i, s = 0, { instant = false } = {}) {
    const prev = slides[cur];
    const next = slides[i];
    const total = next.__steps.length;
    s = s === "end" ? total : Math.max(0, Math.min(total, s));
    if (prev !== next) { prev.classList.remove("is-active"); resetSlide(prev); }
    else resetSlide(next);
    cur = i; step = s;
    const quiet = instant || REDUCED;
    if (quiet) next.classList.add("sf-instant");
    next.classList.add("is-active");
    void next.offsetWidth;                         // commit hidden state before transitions
    next.classList.add("is-played");
    entrance(next, quiet);
    for (let k = 0; k < s; k++) revealStep(next, k, true);
    markPast(next, s);
    if (quiet) raf2().then(() => next.classList.remove("sf-instant"));
    afterChange();
  }

  function go(i, s = 0, opts = {}) {
    if (i < 0 || i >= N) return;
    const dir = opts.dir ?? (i >= cur ? 1 : -1);
    const kind = slides[i].dataset.transition || slides[cur].dataset.transitionOut || cfg.transition;
    const canVT = MODE === "show" && !REDUCED && !opts.instant && i !== cur && kind !== "none" && document.startViewTransition;
    if (!canVT) return activate(i, s, opts);
    if (vtRunning) vtRunning.skipTransition();
    const flavour = kind === "slide" ? (dir < 0 ? "slide-prev" : "slide-next") : `${kind}-${dir < 0 ? "prev" : "next"}`;
    root.dataset.vt = flavour;
    const from = slides[cur];
    setMorph(from, true);
    const vt = document.startViewTransition(() => { setMorph(from, false); activate(i, s, opts); setMorph(slides[i], true); });
    vtRunning = vt;
    vt.finished.finally(() => { setMorph(slides[i], false); if (vtRunning === vt) { vtRunning = null; delete root.dataset.vt; } });
  }
  // data-morph="key": same key on consecutive slides → element glides between positions (Magic Move)
  function setMorph(slide, on) {
    slide.querySelectorAll("[data-morph]").forEach((el) => (el.style.viewTransitionName = on ? "m-" + el.dataset.morph.replace(/[^\w-]/g, "_") : ""));
  }

  function next() {
    const slide = slides[cur];
    if (step < slide.__steps.length) { revealStep(slide, step, REDUCED); step++; markPast(slide, step); afterChange(); }
    else go(cur + 1, 0, { dir: 1 });
  }
  function prev() {
    const slide = slides[cur];
    if (step > 0) { step--; hideStep(slide, step); markPast(slide, step); afterChange(); }
    else go(cur - 1, "end", { dir: -1 });
  }

  /* === CHROME (progress, page number, footer) === */
  let chrome;
  function buildChrome() {
    if (!cfg.chrome || MODE === "embed") return;
    chrome = document.createElement("div");
    chrome.className = "deck-chrome is-global"; chrome.dataset.rt = "";
    chrome.innerHTML = `<div class="deck-progress"><i></i></div><div class="deck-footer"></div><div class="deck-pageno"></div>`;
    chrome.querySelector(".deck-footer").textContent = cfg.footer || "";
    stage.append(chrome);
  }
  function afterChange() {
    const slide = slides[cur];
    if (chrome) {
      chrome.classList.toggle("is-hidden", slide.dataset.chrome === "off");
      chrome.style.setProperty("--progress", N > 1 ? cur / (N - 1) : 1);
      chrome.querySelector(".deck-pageno").textContent = `${String(cur + 1).padStart(2, "0")} / ${String(N).padStart(2, "0")}`;
      chrome.style.color = getComputedStyle(slide).color;
    }
    if (MODE === "show") {
      history.replaceState(null, "", `#/${cur + 1}${step ? "." + step : ""}`);
      if (presenterWin && !presenterWin.closed) presenterWin.postMessage({ sf: "state", i: cur, s: step }, "*");
    }
    document.dispatchEvent(new CustomEvent("deck:change", { detail: { index: cur, step } }));
  }

  /* === SCALE === */
  function fit() {
    const s = Math.min(innerWidth / 1920, innerHeight / 1080);
    stage.style.setProperty("--scale", s);
    if (overview?.classList.contains("show")) sizeThumbs();
  }

  /* === data-fit: shrink text until it fits its box (safety net for big numbers) === */
  function fitText() {
    document.querySelectorAll("[data-fit]").forEach((el) => {
      el.style.fontSize = "";
      let fs = parseFloat(getComputedStyle(el).fontSize), guard = 60;
      while (guard-- > 0 && fs > 14 && (el.scrollWidth > el.clientWidth + 1 || el.scrollHeight > el.clientHeight + 1)) {
        fs *= 0.95; el.style.fontSize = fs + "px";
      }
    });
  }

  /* === OVERVIEW (O) === */
  let overview;
  function buildOverview() {
    overview = document.createElement("div");
    overview.className = "deck-overview"; overview.dataset.rt = "";
    slides.forEach((s, i) => {
      const th = document.createElement("div"); th.className = "thumb"; th.dataset.i = i;
      const inner = document.createElement("div"); inner.className = "inner";
      const c = s.cloneNode(true);
      c.removeAttribute("id"); c.querySelectorAll("[id]").forEach((n) => n.removeAttribute("id"));
      c.classList.add("is-active", "is-played");
      c.querySelectorAll("[data-count]").forEach((n) => (n.textContent = n.textContent)); // freeze
      inner.append(c); th.append(inner);
      const no = document.createElement("span"); no.className = "no"; no.textContent = i + 1; th.append(no);
      th.onclick = () => { toggleOverview(false); go(i, 0, { instant: true }); };
      overview.append(th);
    });
    document.body.append(overview);
  }
  function sizeThumbs() {
    overview.querySelectorAll(".thumb").forEach((th) => {
      th.querySelector(".inner").style.transform = `scale(${th.clientWidth / 1920})`;
      th.classList.toggle("current", +th.dataset.i === cur);
    });
  }
  function toggleOverview(force) {
    if (!overview) buildOverview();
    const on = force ?? !overview.classList.contains("show");
    overview.classList.toggle("show", on);
    if (on) { sizeThumbs(); overview.querySelector(".current")?.scrollIntoView({ block: "center" }); }
  }

  /* === BLACKOUT (B / .) === */
  let black;
  function toggleBlack() {
    if (!black) { black = document.createElement("div"); black.dataset.rt = ""; black.style.cssText = "position:fixed;inset:0;background:#000;z-index:70;display:none"; document.body.append(black); }
    black.style.display = black.style.display === "none" ? "block" : "none";
  }

  /* === HELP (?) & HUD === */
  let help, hud;
  function buildHelp() {
    help = document.createElement("div"); help.className = "deck-help"; help.dataset.rt = "";
    const rows = [
      ["→ / Space", T("次へ（ステップ→スライド）", "Next (step → slide)")], ["←", T("戻る", "Back")],
      ["O", T("一覧（サムネイル）", "Overview")], ["S", T("発表者ビュー（ノート・タイマー）", "Speaker view")],
      ["F", T("フルスクリーン", "Fullscreen")], ["B", T("ブラックアウト", "Blackout")],
      ["E", T("文字を直接編集 → Ctrl/⌘+S で保存", "Edit text → Ctrl/⌘+S to save")],
      ["12 ⏎", T("12枚目へジャンプ", "Jump to slide 12")], ["Home / End", T("最初 / 最後", "First / last")],
    ];
    help.innerHTML = `<div class="box"><h3 style="margin:0 0 16px;font-size:18px">${T("キーボード操作", "Keyboard")}</h3>${rows.map(([k, v]) => `<div><kbd>${k}</kbd>${v}</div>`).join("")}</div>`;
    help.onclick = () => help.classList.remove("show");
    document.body.append(help);
    hud = document.createElement("div"); hud.className = "deck-hud"; hud.dataset.rt = ""; document.body.append(hud);
  }
  function flash(msg, ms = 1800) { if (!hud) return; hud.textContent = msg; hud.classList.add("show"); clearTimeout(hud.__t); hud.__t = setTimeout(() => hud.classList.remove("show"), ms); }

  /* === INLINE EDIT (E) + SAVE (Ctrl/⌘+S) — saves a clean file without runtime artefacts === */
  const EDITABLE = "h1,h2,h3,h4,p,li,.hero,.statement,.lede,.kicker,.quote,.quote-by,figcaption,.caption,td,th,.value,.label,.bar .k,.bar .v,.col-bar .k,.col-bar .v,.tag,.when,.pill,.sec-no,.meta > *";
  let editing = false;
  function toggleEdit() {
    editing = !editing;
    root.classList.toggle("is-editing", editing);
    stage.querySelectorAll(":scope > .slide").forEach((s) => s.querySelectorAll(EDITABLE).forEach((el) => {
      if (editing) { el.setAttribute("contenteditable", "true"); el.setAttribute("data-editable", ""); }
      else { el.removeAttribute("contenteditable"); el.removeAttribute("data-editable"); }
    }));
    stage.querySelectorAll("[data-count]").forEach(finishCount);
    flash(editing ? T("編集モード：文字をクリックして編集 / Ctrl+S で保存 / Esc で終了", "Edit mode: click text · Ctrl+S save · Esc exit") : T("編集モード終了", "Edit mode off"), 3000);
  }
  function save() {
    const doc = new DOMParser().parseFromString(PRISTINE, "text/html");
    if (window.__SF_PRISTINE_STAGE != null) doc.querySelector(".deck-stage").innerHTML = window.__SF_PRISTINE_STAGE;   // slides before slides-fx.js touched them
    const liveSlides = [...stage.querySelectorAll(":scope > section.slide")];
    const srcSlides = [...doc.querySelectorAll(".deck-stage > section.slide")];
    liveSlides.forEach((ls, i) => {
      const a = [...ls.querySelectorAll(EDITABLE)], b = [...(srcSlides[i]?.querySelectorAll(EDITABLE) || [])];
      a.forEach((el, k) => {
        if (!b[k]) return;
        const c = el.cloneNode(true);
        c.querySelectorAll("[data-rt]").forEach((n) => n.remove());
        c.querySelectorAll("span.ch, span.sf-c, span.sf-w").forEach((s) => s.replaceWith(s.textContent));
        c.querySelectorAll("[contenteditable],[data-editable]").forEach((n) => { n.removeAttribute("contenteditable"); n.removeAttribute("data-editable"); });
        c.querySelectorAll("[style]").forEach((n) => {   // strip only what the runtime added; keep author styles
          ["--delay", "--bar-delay", "--len", "--d", "--k", "--n", "--line", "stroke-dasharray", "stroke-dashoffset", "view-transition-name", "transition-delay"].forEach((k) => n.style.removeProperty(k));
          if (n.hasAttribute("data-fit")) n.style.removeProperty("font-size");
          if (!n.getAttribute("style").trim()) n.removeAttribute("style");
        });
        c.querySelectorAll("[class]").forEach((n) => {
          n.classList.remove("is-in", "is-past", "is-played", "is-active", "sf-instant");
          [...n.classList].filter((k) => k.startsWith("sf-annotated")).forEach((k) => n.classList.remove(k));
          if (!n.classList.length) n.removeAttribute("class");
        });
        b[k].innerHTML = c.innerHTML;
      });
    });
    const html = "<!DOCTYPE html>\n" + doc.documentElement.outerHTML;
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([html], { type: "text/html" }));
    a.download = decodeURIComponent(location.pathname.split("/").pop() || "deck.html");
    a.click();
    flash(T("保存しました（ダウンロードされたファイルで元のファイルを置き換えてください）", "Saved (replace the original with the downloaded file)"), 3500);
  }

  /* === PRESENTER VIEW (S) === */
  function openPresenter() {
    const url = location.href.split("#")[0].replace(/[?&]presenter/, "");
    presenterWin = window.open(url + (url.includes("?") ? "&" : "?") + "presenter#/" + (cur + 1), "sf-presenter", "width=1400,height=860");
    setTimeout(() => presenterWin?.postMessage({ sf: "state", i: cur, s: step }, "*"), 800);
  }
  function runPresenter() {
    const base = location.href.split("#")[0].split("?")[0];
    document.body.innerHTML = "";
    document.body.style.cssText = "margin:0;background:#101014;color:#eee;font:15px/1.6 system-ui,sans-serif;overflow:hidden";
    const ui = document.createElement("div");
    ui.style.cssText = "display:grid;grid-template-columns:1.55fr 1fr;grid-template-rows:auto 1fr;gap:16px;padding:16px;height:100vh;box-sizing:border-box";
    ui.innerHTML = `
      <div style="grid-column:1/-1;display:flex;gap:28px;align-items:center;font-variant-numeric:tabular-nums">
        <b id="p-no" style="font-size:22px"></b><span id="p-timer" title="${T("クリックでリセット", "click to reset")}" style="font-size:22px;cursor:pointer">00:00</span>
        <span id="p-clock" style="opacity:.6"></span><span style="margin-left:auto;opacity:.5">${T("← → で操作 / このウィンドウからも進められます", "← → to navigate")}</span></div>
      <div style="display:flex;flex-direction:column;gap:8px;min-height:0"><div style="opacity:.6">${T("現在", "Now")}</div>
        <div style="position:relative;aspect-ratio:16/9;background:#000;border-radius:8px;overflow:hidden"><iframe id="p-cur" style="position:absolute;inset:0;width:100%;height:100%;border:0"></iframe></div></div>
      <div style="display:flex;flex-direction:column;gap:8px;min-height:0"><div style="opacity:.6">${T("次", "Next")}</div>
        <div style="position:relative;aspect-ratio:16/9;background:#000;border-radius:8px;overflow:hidden;opacity:.85"><iframe id="p-next" style="position:absolute;inset:0;width:100%;height:100%;border:0"></iframe></div>
        <div style="opacity:.6;margin-top:8px">${T("ノート", "Notes")}</div><div id="p-notes" style="overflow:auto;font-size:20px;line-height:1.75;padding-right:8px;flex:1"></div></div>`;
    document.body.append(ui);
    const $ = (id) => document.getElementById(id);
    $("p-cur").src = base + "?embed#/1"; $("p-next").src = base + "?embed#/2";
    let t0 = Date.now(); $("p-timer").onclick = () => (t0 = Date.now());
    setInterval(() => {
      const s = Math.floor((Date.now() - t0) / 1000);
      $("p-timer").textContent = `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
      $("p-clock").textContent = new Date().toLocaleTimeString(JA ? "ja-JP" : "en-US", { hour: "2-digit", minute: "2-digit" });
    }, 500);
    let pi = 0, ps = 0;
    const show = (i, s) => {
      pi = i; ps = s;
      const total = slides[i].__steps.length;
      $("p-no").textContent = `${i + 1} / ${N}` + (total ? `  ·  step ${s}/${total}` : "");
      $("p-notes").innerHTML = slides[i].querySelector("aside.notes")?.innerHTML || `<span style="opacity:.4">${T("（ノートなし）", "(no notes)")}</span>`;
      $("p-cur").contentWindow?.postMessage({ sf: "goto", i, s }, "*");
      const nx = s < total ? [i, s + 1] : [i + 1, 0];
      if (nx[0] < N) $("p-next").contentWindow?.postMessage({ sf: "goto", i: nx[0], s: nx[1] }, "*");
    };
    addEventListener("message", (e) => { if (e.data?.sf === "state") show(e.data.i, e.data.s); });
    ["p-cur", "p-next"].forEach((id) => $(id).addEventListener("load", () => setTimeout(() => show(pi, ps), 300)));
    addEventListener("keydown", (e) => {
      const nav = ["ArrowRight", "ArrowDown", " ", "PageDown", "Enter"].includes(e.key) ? 1 : ["ArrowLeft", "ArrowUp", "PageUp", "Backspace"].includes(e.key) ? -1 : 0;
      if (!nav) return; e.preventDefault();
      if (window.opener) window.opener.postMessage({ sf: "nav", dir: nav }, "*");
    });
  }

  /* === INPUT === */
  let jumpBuf = "";
  function onKey(e) {
    if (editing) {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "s") { e.preventDefault(); save(); }
      else if (e.key === "Escape") toggleEdit();
      return;
    }
    if (e.ctrlKey || e.metaKey || e.altKey) return;
    const k = e.key;
    if (/^\d$/.test(k)) { jumpBuf += k; flash("→ " + jumpBuf); return; }
    if (k === "Enter" && jumpBuf) { go(+jumpBuf - 1, 0, { instant: true }); jumpBuf = ""; return; }
    jumpBuf = "";
    if (overview?.classList.contains("show") && (k === "Escape" || k === "o" || k === "O")) return toggleOverview(false);
    if (help?.classList.contains("show")) { help.classList.remove("show"); if (k === "Escape") return; }
    switch (k) {
      case "ArrowRight": case "ArrowDown": case " ": case "PageDown": case "Enter": case "n": e.preventDefault(); next(); break;
      case "ArrowLeft": case "ArrowUp": case "PageUp": case "Backspace": case "p": e.preventDefault(); prev(); break;
      case "Home": go(0, 0, { instant: true }); break;
      case "End": go(N - 1, "end", { instant: true }); break;
      case "o": case "O": case "Escape": toggleOverview(); break;
      case "f": case "F": document.fullscreenElement ? document.exitFullscreen() : root.requestFullscreen?.(); break;
      case "b": case "B": case ".": toggleBlack(); break;
      case "s": case "S": openPresenter(); break;
      case "e": case "E": toggleEdit(); break;
      case "?": case "h": case "H": help.classList.toggle("show"); break;
    }
  }
  function bindPointer() {
    viewport.addEventListener("click", (e) => {
      if (editing || e.target.closest("a,button,input,textarea,select,video,[data-no-nav]")) return;
      if (getSelection()?.toString()) return;
      e.clientX < innerWidth * 0.3 ? prev() : next();
    });
    let x0 = null, y0 = null;
    viewport.addEventListener("touchstart", (e) => { x0 = e.touches[0].clientX; y0 = e.touches[0].clientY; }, { passive: true });
    viewport.addEventListener("touchend", (e) => {
      if (x0 == null) return;
      const dx = e.changedTouches[0].clientX - x0, dy = e.changedTouches[0].clientY - y0;
      if (Math.abs(dx) > 50 && Math.abs(dx) > Math.abs(dy)) (dx < 0 ? next : prev)();
      x0 = null;
    }, { passive: true });
  }

  function parseHash() {
    const m = location.hash.match(/#\/(\d+)(?:\.(\d+))?/);
    return m ? [Math.min(N, Math.max(1, +m[1])) - 1, +(m[2] || 0)] : [0, 0];
  }

  /* === EXPORT MODE: everything visible, final state, page numbers per slide === */
  function runExport() {
    root.classList.add("is-export");
    slides.forEach((s, i) => {
      s.classList.add("is-active", "is-played", "sf-instant");
      s.querySelectorAll("[data-anim]").forEach((el) => { el.style.setProperty("--delay", "0ms"); el.classList.add("is-in"); });
      s.querySelectorAll("[data-count]").forEach(finishCount);
      if (cfg.chrome && s.dataset.chrome !== "off" && !qs.has("nochrome")) {
        const f = document.createElement("div"); f.className = "deck-chrome"; f.dataset.rt = "";
        f.innerHTML = `<div class="deck-footer"></div><div class="deck-pageno">${String(i + 1).padStart(2, "0")} / ${String(N).padStart(2, "0")}</div>`;
        f.querySelector(".deck-footer").textContent = cfg.footer || "";
        s.append(f);
      }
    });
  }

  /* === BOOT === */
  const ready = (async () => {
    if (MODE === "presenter") { runPresenter(); return; }
    if (MODE === "export") runExport();
    else {
      buildChrome(); fit(); addEventListener("resize", fit);
      if (MODE === "show") { buildHelp(); addEventListener("keydown", onKey); bindPointer(); }
      addEventListener("message", (e) => {
        if (e.data?.sf === "nav") (e.data.dir > 0 ? next : prev)();
        if (e.data?.sf === "goto") activate(e.data.i, e.data.s, { instant: true });
      });
      addEventListener("hashchange", () => { const [i, s] = parseHash(); if (i !== cur || s !== step) go(i, s, { instant: true }); });
    }
    try { await document.fonts.ready; } catch (e) {}
    fitText();
    document.dispatchEvent(new CustomEvent("deck:layout"));      // fonts + fitted text settled: effects measure now (slides-fx.js)
    if (MODE !== "export") {
      const [i, s] = parseHash();
      slides.forEach((sl) => sl.classList.remove("is-active"));
      cur = i; activate(i, s, { instant: MODE === "embed" });
      if (MODE === "show" && !sessionStorage.getItem("sf-hint")) {
        setTimeout(() => flash(T("? で操作ヘルプ ・ S で発表者ビュー ・ O で一覧", "? help · S speaker view · O overview"), 3200), 600);
        try { sessionStorage.setItem("sf-hint", 1); } catch (e) {}
      }
    }
    await raf2();
    root.classList.add("sf-ready");
  })();

  window.deck = {
    get count() { return N; }, get index() { return cur; }, get step() { return step; },
    steps: (i = cur) => slides[i].__steps.length,
    go: (i, s = 0, opts = {}) => go(i, s, opts), next, prev, ready, mode: MODE, config: cfg,
    slides: () => slides,
  };
})();
