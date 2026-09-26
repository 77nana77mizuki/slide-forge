#!/usr/bin/env python3
"""Visual pipeline test (offline): local library → search → contact sheet → pick (crop+duotone) →
icons in deck → build (captions, credits slide, licence lint) → check (0 errors) → negative cases
(text-on-image, low-res, unrecorded image) are detected.   Usage: python tests/test_visuals.py [workdir]"""
import json, os, random, subprocess, sys, tempfile
from pathlib import Path
from PIL import Image, ImageDraw

SF = Path(__file__).resolve().parents[1] / "skills" / "slide-forge" / "scripts"
W = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(tempfile.mkdtemp(prefix="sf-vis-"))
(W / "lib").mkdir(parents=True, exist_ok=True); (W / "deck").mkdir(exist_ok=True)
fails = []
def ok(c, m):
    print(("PASS " if c else "FAIL ") + m)
    if not c: fails.append(m)
def run(*args, cwd=W / "deck"):
    r = subprocess.run([sys.executable, *map(str, args)], cwd=cwd, capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr

random.seed(7)
def pic(name, w, h, c1, c2, meta=None):
    im = Image.new("RGB", (w, h), c1); d = ImageDraw.Draw(im)
    for y in range(h):
        t = y / h; d.line([(0, y), (w, y)], fill=tuple(int(c1[k] * (1 - t) + c2[k] * t) for k in range(3)))
    for _ in range(8):
        x, y, r = random.randint(0, w), random.randint(0, h), random.randint(40, 220)
        d.ellipse([x - r, y - r, x + r, y + r], fill=tuple(random.randint(40, 230) for _ in range(3)))
    im.save(W / "lib" / f"{name}.jpg", quality=88)
    if meta: (W / "lib" / f"{name}.jpg.json").write_text(json.dumps(meta, ensure_ascii=False))
pic("factory-line", 3000, 2000, (20, 40, 80), (200, 210, 230), {"license": "CC BY 4.0", "creator": "Test Author", "title": "Line", "tags": ["工場"]})
pic("factory-nc", 3000, 2000, (20, 40, 80), (90, 90, 90), {"license": "CC BY-NC 4.0", "creator": "NC"})
pic("tiny", 500, 320, (90, 20, 20), (250, 220, 220), {"license": "CC0"})
Image.new("RGB", (2400, 1350), (236, 230, 214)).save(W / "lib" / "bright.jpg")

rc, out = run(SF / "assets.py", "search", "factory", "--sources", f"local:{W/'lib'}", "--min-width", "400")
ok(rc == 0 and "1 nc" in out, "search excludes NC licence")
cand = W / "deck" / "img" / "_cand" / "factory"
ok((cand / "sheet.png").exists(), "contact sheet written")
names = [c["title"] for c in json.loads((cand / "candidates.json").read_text())["candidates"]]
rc, out = run(SF / "assets.py", "pick", cand, str(names.index("Line") + 1), "--as", "img/line.jpg", "--crop", "16:9", "--treat", "duotone", "--theme", "signal")
ok(rc == 0 and Image.open(W / "deck/img/line.jpg").size == (2400, 1350), "pick crops 16:9 and resizes to 2400px")
cr = json.loads((W / "deck/credits.json").read_text())
ok(cr["img/line.jpg"]["attribution_required"] and "duotone" in cr["img/line.jpg"]["modified"], "licence + modifications recorded")
run(SF / "assets.py", "search", "tiny", "--sources", f"local:{W/'lib'}", "--min-width", "100")
rc, out = run(SF / "assets.py", "pick", W / "deck/img/_cand/tiny", "1", "--as", "img/tiny.jpg")
import shutil; shutil.copy(W / "lib/bright.jpg", W / "deck/img/bright.jpg"); shutil.copy(W / "lib/tiny.jpg", W / "deck/img/unrecorded.jpg")
run(SF / "assets.py", "add", "img/bright.jpg", "--own")

(W / "deck/deck.src.html").write_text("""<script type="application/json" id="deck-config">{"title":"t","theme":"signal","density":"speaker"}</script>
<section class="slide L-title" data-chrome="off"><div class="media-bg"><img src="img/line.jpg" alt="a"></div><h1 class="hero">現場の自動化は、次の段階へ</h1></section>
<section class="slide L-cards"><div class="head"><h2 class="headline">三つの打ち手で止まらないラインにする</h2></div>
  <div class="icon-row" style="--cols:3"><div><i class="ico" data-icon="tabler:robot"></i><h3>搬送</h3></div><div><i class="ico" data-icon="tabler:eye-check"></i><h3>検査</h3></div><div><i class="ico" data-icon="tabler:package"></i><h3>梱包</h3></div></div><aside class="notes">n</aside></section>
""", encoding="utf-8")
rc, out = run(SF / "build.py", "deck.src.html", "--fonts", "none")
html = (W / "deck/deck.html").read_text()
ok(html.count("<svg") >= 3 and 'data-icon="tabler:robot" aria-hidden="true"><svg' in html, "data-icon resolved to inline SVG")
ok('class="credit"' in html, "attribution caption inserted for CC BY image")
ok("L-credits" in html and "Test Author" in html, "credits slide appended")
rc, out = run(SF / "check.py", "deck.html", "--out", "qa", "--no-shots")
ok(" 0 errors" in out, "good deck passes check" + ("" if " 0 errors" in out else "\n" + out))

src = (W / "deck/deck.src.html").read_text()
src += """<section class="slide L-free"><div class="media-bg none"><img src="img/bright.jpg" alt="b"></div><h2 class="headline" style="color:#fff">明るい写真に白い文字を置いた悪い例</h2><aside class="notes">n</aside></section>
<section class="slide L-split"><div class="head"><h2 class="headline">小さい画像を大きく表示した例</h2></div><div class="col"><p>x</p></div><div class="col"><div class="frame" style="height:700px"><img class="photo" src="img/tiny.jpg" alt="t"></div></div><aside class="notes">n</aside></section>
<section class="slide L-free"><h2 class="headline">記録のない画像</h2><img src="img/unrecorded.jpg" alt="u" style="width:400px"><aside class="notes">n</aside></section>"""
(W / "deck/bad.src.html").write_text(src, encoding="utf-8")
rc, out = run(SF / "build.py", "bad.src.html", "--fonts", "none")
ok("img/unrecorded.jpg has no licence record" in out, "build warns about unrecorded image")
rc, out = run(SF / "check.py", "bad.html", "--out", "qa-bad", "--no-shots")
ok("text-on-image" in out, "detects unreadable text on photo")
ok("low-res" in out, "detects upscaled low-res image")
# regression: url() inside style="" must survive inlining (quotes would terminate the attribute)
(W / "deck/bg.src.html").write_text("""<script type="application/json" id="deck-config">{"title":"t","theme":"signal","credits":"off"}</script>
<section class="slide L-free"><h2 class="headline">背景画像のテスト</h2><div class="bgimg" style="--tex:url(img/line.jpg);width:400px;height:200px;background-image:var(--tex)"></div><aside class="notes">n</aside></section>""", encoding="utf-8")
run(SF / "build.py", "bg.src.html", "--fonts", "none")
import re as _re
m = _re.search(r'<div class="bgimg" style="([^"]*)"', (W / "deck/bg.html").read_text())
ok(m is not None and "data:image/jpeg;base64," in m.group(1) and m.group(1).rstrip().endswith("var(--tex)"), "url() in style attribute inlined without breaking the attribute")
print(f"{'✗' if fails else '✓'} visual tests: {len(fails)} failed  (workdir {W})")
sys.exit(1 if fails else 0)
