#!/usr/bin/env python3
"""Interaction tests for slides-fx.js (v1.7 expressive effects) on the fx showcase deck.

    python3 tests/test_fx.py path/to/fx.html
"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

deck = Path(sys.argv[1]).resolve().as_uri()
ok = fail = 0


def check(name, cond, info=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  ✓ {name}")
    else:
        fail += 1
        print(f"  ✗ FAIL {name} {info}")


def slide_index(page, text):
    return page.evaluate("(t) => [...document.querySelectorAll('.deck-stage > section.slide')].findIndex(s => s.querySelector(t))", text)


with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1920, "height": 1080})
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(deck)
    pg.wait_for_function("document.documentElement.classList.contains('sf-ready')")

    # markers become clicks
    z = slide_index(pg, ".zoom-view")
    check("zoom stops are clicks", pg.evaluate(f"deck.steps({z})") == 4)
    pg.evaluate(f"deck.go({z}, 0, {{instant: true}})")
    pg.wait_for_timeout(200)
    s0 = pg.evaluate("() => new DOMMatrix(getComputedStyle(document.querySelector('.zoom-canvas')).transform).a")
    pg.evaluate("deck.next()")
    pg.wait_for_timeout(1600)
    s1 = pg.evaluate("() => new DOMMatrix(getComputedStyle(document.querySelector('.zoom-canvas')).transform).a")
    check("zoom camera moves in", s1 > s0 * 1.5, f"{s0} → {s1}")
    check("focused region marked", pg.evaluate("document.querySelector('[data-zoom].is-focus')?.dataset.zoom") == "1")
    pg.evaluate("deck.prev()")
    pg.wait_for_timeout(1600)
    s2 = pg.evaluate("() => new DOMMatrix(getComputedStyle(document.querySelector('.zoom-canvas')).transform).a")
    check("zoom back to overview", abs(s2 - s0) < 1e-3, f"{s0} vs {s2}")

    c = slide_index(pg, "[data-codemove]")
    check("code versions are clicks", pg.evaluate(f"deck.steps({c})") == 2)
    pg.evaluate(f"deck.go({c}, 0, {{instant: true}})")
    pg.wait_for_timeout(200)
    t0 = pg.evaluate("document.querySelector('.cm-view').textContent")
    pg.evaluate("deck.next()")
    pg.wait_for_timeout(200)
    moving = pg.evaluate("document.querySelector('.cm-view').getAnimations({subtree: true}).length")
    pg.wait_for_timeout(1000)
    t1 = pg.evaluate("document.querySelector('.cm-view').textContent")
    check("code v1 → v2", "method" not in t0 and "method" in t1)
    check("tokens animate (FLIP)", moving > 0, str(moving))
    check("syntax colouring", pg.evaluate("document.querySelectorAll('.cm-view .t.k').length") > 0)

    s = slide_index(pg, ".ba-slider")
    pg.evaluate(f"deck.go({s}, 'end', {{instant: true}})")
    pg.wait_for_timeout(300)
    check("slider stop via click", pg.evaluate("getComputedStyle(document.querySelector('.ba-slider')).getPropertyValue('--pos').trim()") == "12%")

    a = slide_index(pg, "[data-annotate]")
    pg.evaluate(f"deck.go({a}, 'end', {{instant: true}})")
    pg.wait_for_timeout(300)
    check("annotation drawn", pg.evaluate("document.querySelector('.sf-annot path')?.getAttribute('d')?.length || 0") > 20)

    g = slide_index(pg, "[data-3d='globe']")
    pg.evaluate(f"deck.go({g}, 0, {{instant: true}})")
    pg.wait_for_timeout(1200)
    check("3d canvas", pg.evaluate("!!document.querySelector('[data-3d=globe] canvas.sf-3d-canvas')"))
    pg.evaluate("deck.go(0, 0, {instant: true})")
    pg.wait_for_timeout(200)
    check("3d stops off-slide", pg.evaluate("!document.querySelector('[data-3d=globe]').__running"))

    check("pristine source has no runtime markers", pg.evaluate("() => !window.__SF_PRISTINE_STAGE.includes('sf-mark')"))
    check("no page errors", not errs, "; ".join(errs))

    # export: final states
    pe = b.new_page(viewport={"width": 1920, "height": 1080})
    pe.goto(deck + "?export")
    pe.wait_for_function("document.documentElement.classList.contains('sf-ready')")
    pe.wait_for_timeout(300)
    check("export: last code version", "notify" in pe.evaluate("document.querySelector('.cm-view').textContent"))
    check("export: scramble settled", pe.evaluate("document.querySelector('[data-anim=scramble]').textContent") == "18.4%")
    check("export: zoom overview", pe.evaluate("!document.querySelector('.zoom-view').classList.contains('is-zoomed')"))
    b.close()

print(f"fx: {ok} passed, {fail} failed")
