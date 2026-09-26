#!/usr/bin/env python3
"""Video pipeline test: scaffold → add media → check (positive + negative) → stills (all scene types) → determinism,
then the motion pack: motion example (kinetic/stat/steps/bars, transitions, light leak), negative checks, filmstrip, flash check.
Usage: python3 tests/test_video.py OUT_DIR      (skips cleanly when node/npm are unavailable)"""
import json, shutil, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VP = ROOT / "skills/slide-forge/scripts/video.py"
out = Path(sys.argv[1] if len(sys.argv) > 1 else ROOT / "tests/_out/video"); shutil.rmtree(out, ignore_errors=True); out.mkdir(parents=True)
passed = failed = 0


def ok(name, cond, extra=""):
    global passed, failed
    print(("PASS " if cond else "FAIL ") + name + (f"  {extra}" if extra and not cond else ""))
    passed += bool(cond); failed += (not cond)


def vp(*a, check=False):
    r = subprocess.run([sys.executable, str(VP), *map(str, a)], capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


if not (shutil.which("node") and shutil.which("npm")):
    print("SKIP video (node/npm not found)\n0 passed, 0 failed"); sys.exit(0)

# synthetic media (no network): a banded "planet" texture and a photo with its sidecar licence
from PIL import Image, ImageDraw
media = out / "src-media"; media.mkdir()
tex = Image.new("RGB", (1024, 512)); d = ImageDraw.Draw(tex)
for y in range(0, 512, 16):
    d.rectangle([0, y, 1024, y + 16], fill=(180 + (y * 7) % 60, 120 + (y * 3) % 80, 70))
tex.save(media / "planet.jpg")
ph = Image.new("RGB", (1600, 900)); d = ImageDraw.Draw(ph)
for x in range(0, 1600, 4):
    d.line([x, 0, x, 900], fill=(30 + x // 20, 60 + x // 40, 90))
d.ellipse([1000, 250, 1400, 650], fill=(240, 200, 120)); ph.save(media / "photo.jpg")
for n in ("planet.jpg", "photo.jpg"):
    (media / f"{n}.json").write_text(json.dumps({"license": "CC0", "creator": "test", "source": "synthetic"}))

P = out / "proj"
rc, log = vp("new", P, "--theme", "washi")
ok("new: scaffold with theme", rc == 0 and (P / "storyboard.json").exists() and (P / "src/Scenes.tsx").exists(), log)
sb = json.loads((P / "storyboard.json").read_text())
ok("new: theme tokens mapped to style", sb["style"]["bg"].startswith("#") and "Zen" in "".join(sb["fonts"]) or len(sb["fonts"]) > 0, str(sb["style"]))
rc, log = vp("add", P, media / "planet.jpg", media / "photo.jpg")
cr = json.loads((P / "credits.json").read_text())
ok("add: copies media + records sidecar licence", rc == 0 and cr.get("media/photo.jpg", {}).get("license") == "CC0", log)
cp = media / "icon.png"; ph.resize((64, 36)).save(cp)
rc, log = vp("add", P, cp, "--license", "CC0", "--creator", "3dicons", "--source", "https://3dicons.co")
cr = json.loads((P / "credits.json").read_text())
ok("add: --license records a verified licence", rc == 0 and cr.get("media/icon.png", {}).get("license") == "CC0", log)

sb.update(fps=30, width=1920, height=1080, sky=None, transition={"type": "fade", "seconds": 0.5})
sb["scenes"] = [
    {"type": "title", "seconds": 3, "kicker": "Test", "title": "動画パイプラインの検査", "sub": "全シーン種別", "backdrop": "plain"},
    {"type": "photo", "seconds": 3, "image": "media/photo.jpg", "side": "right", "kicker": "Photo", "title": "写真にゆっくり寄る", "big": "72", "unit": "%", "credit": "画像: test (CC0)"},
    {"type": "globe", "seconds": 3, "texture": "media/planet.jpg", "side": "left", "ring": True, "title": "球体と環を描く", "credit": "画像: test (CC0)"},
    {"type": "end", "seconds": 3, "title": "おわり", "backdrop": "media/photo.jpg", "credit": "画像: test (CC0)"},
]
(P / "storyboard.json").write_text(json.dumps(sb, ensure_ascii=False, indent=2))
rc, log = vp("check", P)
ok("check: valid storyboard → 0 errors", rc == 0 and "0 errors" in log, log)

bad = json.loads(json.dumps(sb)); bad["scenes"][1]["image"] = "media/missing.jpg"; bad["scenes"].append({"type": "slideshow", "seconds": 3, "title": "x"})
bad["scenes"][2]["title"] = "とても長い見出しは一場面一主張の原則に反するので警告されるべきである"
B = out / "bad"; shutil.copytree(P, B, symlinks=True, ignore=shutil.ignore_patterns("node_modules", "out"))
(B / "storyboard.json").write_text(json.dumps(bad, ensure_ascii=False))
rc, log = vp("check", B)
ok("check: catches missing media", rc == 1 and "missing.jpg not found" in log, log)
ok("check: catches unknown scene type", "unknown type" in log, log)
ok("check: warns on long title", "title" in log and "shorten" in log, log)

rc, log = vp("stills", P, "--scale", "0.25")
stills = sorted((P / "out/stills").glob("f*.png"))
ok("stills: one per scene + sheet", rc == 0 and len(stills) == 4 and (P / "out/sheet.png").exists(), log[-800:])
if stills:
    from PIL import ImageStat
    means = [sum(ImageStat.Stat(Image.open(s).convert("L")).mean) for s in stills]
    ok("stills: frames are not black (textures/fonts waited for)", min(means) > 6, str(means))
    # the globe scene must show the lit planet: brightest region well above background
    g = Image.open(stills[2]).convert("L"); ok("stills: globe rendered (WebGL)", g.getextrema()[1] > 120, str(g.getextrema()))
rc, log = vp("det", P, "--frame", "130")
ok("det: identical frame across renders", rc == 0 and "deterministic" in log, log[-800:])

# ---------------------------------------------------------------- motion graphics pack
M = out / "motion"
rc, log = vp("new", M, "--theme", "signal", "--example", "motion")
sbm = json.loads((M / "storyboard.json").read_text())
ok("motion: example scaffold has kinetic/stat/steps/bars", {"kinetic", "stat", "steps", "bars"} <= {s["type"] for s in sbm["scenes"]}, log)
_setup = vp("setup")[1]; modern = "(Chrome 1" in _setup and "< 149" not in _setup
if not modern:   # keep the test runnable without Chrome 149: swap shader transitions for CSS ones
    for s_ in sbm["scenes"]:
        if s_.get("transition", {}).get("type") not in (None, "fade", "slide", "wipe", "flip", "clockWipe", "iris", "pushCut", "none"):
            s_["transition"]["type"] = "slide"
    (M / "storyboard.json").write_text(json.dumps(sbm, ensure_ascii=False, indent=1))
rc, log = vp("check", M)
ok("motion: example passes check", rc == 0 and "0 errors" in log, log)

bad = json.loads(json.dumps(sbm))
bad["scenes"][1]["effect"] = "wobble"
bad["scenes"][2]["items"] = bad["scenes"][2]["items"][:1]
bad["scenes"][3]["transition"] = {"type": "starwipe", "seconds": 0.5}
bad["motion"] = "frantic"
for k in range(4):
    bad["scenes"].insert(1, {"type": "kinetic", "seconds": 3, "text": "テスト", "transition": {"type": ["iris", "flip", "clockWipe", "pushCut"][k]}})
B2 = out / "motion-bad"; shutil.copytree(M, B2, symlinks=True, ignore=shutil.ignore_patterns("node_modules", "out"))
(B2 / "storyboard.json").write_text(json.dumps(bad, ensure_ascii=False))
rc, log = vp("check", B2)
ok("check: unknown text effect", "effect 'wobble'" in log, log)
ok("check: steps item count", "items must have 2–5" in log, log)
ok("check: unknown transition", "transition 'starwipe' unknown" in log, log)
ok("check: unknown motion preset", "motion: 'frantic'" in log, log)
ok("check: too many transition kinds", "different transitions" in log, log)

rc, log = vp("stills", M, "--scale", "0.25")
st = sorted((M / "out/stills").glob("f*.png"))
ok("motion: stills for every scene", rc == 0 and len(st) == len(sbm["scenes"]), log[-600:])
if st:
    from PIL import ImageStat
    ok("motion: no blank scene", min(sum(ImageStat.Stat(Image.open(p_).convert("L")).stddev) for p_ in st) > 4)
rc, log = vp("motion", M, "--scene", "3", "--n", "6")
ok("motion: filmstrip", rc == 0 and (M / "out/motion-03.png").exists(), log[-600:])
tl_start = 0
rc, log = vp("det", M, "--frame", "600")          # scramble scene + light leak: seeded glyphs must repeat exactly
ok("motion: scramble/noise deterministic", rc == 0 and "deterministic" in log, log[-600:])

# flash check on synthetic clips: 10 Hz full-frame strobe must fail, a slow fade must pass
if shutil.which("ffmpeg"):
    strobe, calm = out / "strobe.mp4", out / "calm.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=black:s=320x180:r=30:d=2", "-vf", "geq=lum='if(lt(mod(N,6),3),230,10)':cb=128:cr=128", "-pix_fmt", "yuv420p", str(strobe)])
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=black:s=320x180:r=30:d=2", "-vf", "geq=lum='20+N*2':cb=128:cr=128", "-pix_fmt", "yuv420p", str(calm)])
    rc1, l1 = vp("flash", strobe); rc2, l2 = vp("flash", calm)
    ok("flash: 5 Hz strobe fails", rc1 == 1, l1)
    ok("flash: slow fade passes", rc2 == 0, l2)

print(f"{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
