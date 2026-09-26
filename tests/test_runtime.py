#!/usr/bin/env python3
"""Runtime interaction tests: navigation, steps, counters, overview, jump, morph,
inline edit + clean save, presenter view, reduced motion.   Usage: python tests/test_runtime.py deck.html"""
import os, sys
from playwright.sync_api import sync_playwright
DECK = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else 'sample.html')
url = 'file://' + DECK
fails = []
def ok(c, m):
    print(('PASS ' if c else 'FAIL ') + m)
    if not c: fails.append(m)
with sync_playwright() as p:
    b=p.chromium.launch(); ctx=b.new_context(viewport={'width':1280,'height':720}, accept_downloads=True); pg=ctx.new_page()
    errs=[]; pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto(url); pg.wait_for_function("document.documentElement.classList.contains('sf-ready')")
    ok(pg.evaluate("deck.count")==16,'16 slides')
    ok(abs(pg.evaluate("parseFloat(getComputedStyle(document.querySelector('.deck-stage')).getPropertyValue('--scale'))")-1280/1920)<.01,'stage scales to viewport')
    pg.evaluate("deck.go(7,0,{instant:true})"); pg.wait_for_timeout(200)
    ok(pg.evaluate("deck.steps()")==7,'slide 8 has 7 build steps')
    ok(pg.evaluate("document.querySelectorAll('.slide.is-active [data-step].is-in').length")==0,'steps hidden on entry')
    pg.keyboard.press('ArrowRight'); pg.keyboard.press('ArrowRight'); pg.wait_for_timeout(100)
    ok(pg.evaluate("deck.step")==2 and pg.evaluate("location.hash")=='#/8.2','two steps revealed, hash #/8.2')
    pg.keyboard.press('ArrowLeft'); pg.wait_for_timeout(100)
    ok(pg.evaluate("deck.step")==1,'back hides one step')
    pg.keyboard.press('ArrowLeft'); pg.keyboard.press('ArrowLeft'); pg.wait_for_timeout(800)
    ok(pg.evaluate("deck.index")==6,'back past step 0 goes to previous slide')
    pg.keyboard.press('ArrowLeft'); pg.wait_for_timeout(800)
    ok(pg.evaluate("deck.index")==5 and pg.evaluate("deck.step")==pg.evaluate("deck.steps()"),'previous slide shown at final state')
    # counters
    pg.evaluate("deck.go(9,0,{instant:true})"); pg.wait_for_timeout(100)
    pg.evaluate("deck.go(9,0)"); pg.wait_for_timeout(3000)
    ok(pg.evaluate("document.querySelector('.slide.is-active .bar .v').textContent")=='95.0%','count-up ends at 95.0%')
    # overview
    pg.keyboard.press('o'); pg.wait_for_timeout(300)
    ok(pg.evaluate("document.querySelectorAll('.deck-overview.show .thumb').length")==16,'overview shows 16 thumbs')
    pg.click('.deck-overview .thumb >> nth=2'); pg.wait_for_timeout(300)
    ok(pg.evaluate("deck.index")==2,'thumbnail click navigates')
    # jump
    pg.keyboard.type('12'); pg.keyboard.press('Enter'); pg.wait_for_timeout(300)
    ok(pg.evaluate("deck.index")==11,'number+Enter jump')
    # morph transition runs without error
    pg.evaluate("deck.go(12,'end',{instant:true})"); pg.wait_for_timeout(200); pg.keyboard.press('ArrowRight'); pg.wait_for_timeout(1200)
    ok(pg.evaluate("deck.index")==13,'morph transition to slide 14')
    # edit + save
    pg.evaluate("deck.go(3,0,{instant:true})"); pg.wait_for_timeout(200)
    pg.keyboard.press('e'); pg.wait_for_timeout(100)
    pg.evaluate("document.querySelector('.slide.is-active .kicker').textContent='EDITED-KICKER'")
    with pg.expect_download() as d: pg.keyboard.press('Control+s')
    path=d.value.path(); html=open(path,encoding='utf-8').read()
    ok('EDITED-KICKER' in html,'edit saved into downloaded HTML')
    stage=html[html.index('<main'):html.index('</main>')]
    ok('class="ch"' not in stage and 'contenteditable' not in stage and 'is-in' not in stage and 'is-active' not in stage and 'deck-chrome' not in stage and '--delay' not in stage,'saved HTML has no runtime artefacts')
    saved=os.path.join(os.path.dirname(DECK),'_saved.html'); open(saved,'w').write(html)
    # presenter window
    pg.keyboard.press('Escape'); pg.wait_for_timeout(100)
    with ctx.expect_page() as np: pg.keyboard.press('s')
    pres=np.value; pres.wait_for_timeout(2500)
    ok('ノート' in pres.content() and pres.evaluate("document.getElementById('p-notes').textContent.length")>5,'presenter view shows notes')
    pres.keyboard.press('ArrowRight'); pg.wait_for_timeout(900)
    ok(pg.evaluate("deck.index")==4,'presenter controls main window')
    ok(not errs,'no JS errors '+str(errs[:3]))
    # saved file reopens and works
    pg2=ctx.new_page(); pg2.goto('file://'+saved); pg2.wait_for_function("document.documentElement.classList.contains('sf-ready')")
    ok(pg2.evaluate("deck.count")==16,'saved file boots as a working deck')
    # reduced motion
    rm=b.new_context(reduced_motion='reduce').new_page(); rm.goto(url+'#/5'); rm.wait_for_function("document.documentElement.classList.contains('sf-ready')"); rm.wait_for_timeout(150)
    ok(rm.evaluate("getComputedStyle(document.querySelector('.slide.is-active .stat')).opacity")=='1','reduced motion: content visible immediately')
    b.close()

print(f'{"✗" if fails else "✓"} runtime tests: {len(fails)} failed')
sys.exit(1 if fails else 0)
