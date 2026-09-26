#!/usr/bin/env python3
"""Slide Forge · video — short cinematic MP4s with Remotion × three.js, driven by one storyboard.json.

A video project is a folder:
    storyboard.json      ← the only file you normally edit (scenes, text, timing, style)
    public/media/        ← images / planet textures (add them with `video.py add`)
    public/fonts.css     ← generated: subset-embedded fonts (`video.py fonts`, automatic on render)
    credits.json         ← licence ledger for everything in public/media
    src/ render.mjs …    ← the template (do not edit for normal work; see references/video.md to extend)
    node_modules → shared runtime (installed once per machine under ~/.cache/slide-forge/video-runtime)

Commands (run `video.py <cmd> -h` for options):
    video.py setup                             install the shared Remotion runtime + a Chrome ≥149 for shader transitions / motion blur
    video.py new DIR [--theme signal] [--motion calm|lively|punchy] [--example solar|motion | --storyboard FILE]
    video.py add DIR FILE... [--as NAME]       copy media into public/media and record credits (sidecar FILE.json or ./credits.json)
    video.py check DIR                         validate storyboard: fields, files, text length, reading time, credits
    video.py fonts DIR                         (re)generate public/fonts.css from the storyboard text
    video.py stills DIR [--scale .5]           one still per scene (after its entrance) + out/sheet.png   ← look at it
    video.py det DIR [--frame N]               determinism check: same frame rendered twice must be identical
    video.py motion DIR --scene N [--n 12]     filmstrip of one scene (entrance → hold → exit) → out/motion-NN.png
    video.py render DIR [--draft] [--out F]    full MP4 (+ contact sheet + photosensitive flash check on the actual video)
    video.py flash FILE.mp4                    WCAG 2.3.1-style flash check (≤3 flashes in any 1 s)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SF = HERE.parent
TEMPLATE = SF / "assets" / "video-template"
THEMES = SF / "assets" / "themes"
CACHE = Path(os.environ.get("SLIDE_FORGE_CACHE", Path.home() / ".cache" / "slide-forge"))
sys.path.insert(0, str(HERE))

SCENE_TYPES = {"title", "end", "globe", "photo", "kinetic", "stat", "steps", "bars", "lottie"}
DEFAULTS = json.loads((TEMPLATE / "src" / "defaults.json").read_text(encoding="utf-8"))
SHADER = set(DEFAULTS["shader"])
CSS_TRANSITIONS = {"none", "fade", "slide", "wipe", "flip", "clockWipe", "iris", "pushCut"}
EFFECTS = {"rise", "pop", "blur", "mask", "slam", "type", "tracking", "scramble", "shimmer"}
PRESETS = {"calm", "lively", "punchy"}
MODERN_CHROME = 149     # HTML-in-canvas (shader transitions, motion blur) needs this
TEMPLATE_FILES = ["src", "render.mjs", "package.json", "tsconfig.json"]
READ_CPS = 10.0           # headline-style on-screen text (full-width chars/second); ASCII counts ×0.3, kicker/number are glanced
TITLE_MAX = {"globe": 26, "photo": 26, "title": 30, "end": 30, "stat": 30, "steps": 30, "bars": 34, "lottie": 26, "kinetic": 48}


def die(msg: str, code: int = 1):
    print(f"✗ {msg}", file=sys.stderr); sys.exit(code)


# ------------------------------------------------------------------ runtime (shared node_modules)
def runtime_dir() -> Path:
    h = hashlib.sha1((TEMPLATE / "package.json").read_bytes()).hexdigest()[:10]
    return CACHE / "video-runtime" / h


def ensure_runtime(verbose=True) -> Path:
    rt = runtime_dir()
    if (rt / "node_modules" / "@remotion" / "renderer").exists():
        return rt
    if not shutil.which("npm"):
        die("Node.js / npm が必要です（https://nodejs.org）。")
    rt.mkdir(parents=True, exist_ok=True)
    shutil.copy2(TEMPLATE / "package.json", rt / "package.json")
    if verbose:
        print(f"  installing Remotion runtime into {rt} (first time only, ~1–3 min) …")
    r = subprocess.run(["npm", "install", "--no-audit", "--no-fund", "--loglevel=error"], cwd=rt)
    if r.returncode != 0:
        die("npm install failed (network to registry.npmjs.org?)")
    return rt


def link_runtime(proj: Path):
    rt = ensure_runtime()
    nm = proj / "node_modules"
    if nm.is_symlink() or nm.exists():
        if nm.is_symlink() and nm.resolve() == (rt / "node_modules").resolve():
            return
        if nm.is_symlink():
            nm.unlink()
        else:
            return  # a real node_modules (user installed locally) — respect it
    nm.symlink_to(rt / "node_modules", target_is_directory=True)


BROWSER_JSON = CACHE / "browser.json"


def chrome_major(path: str | None) -> int:
    if not path or not Path(path).exists():
        return 0
    try:
        out = subprocess.run([path, "--version"], capture_output=True, text=True, timeout=20).stdout
        m = re.search(r"(\d+)\.\d+\.\d+", out)
        return int(m.group(1)) if m else 0
    except Exception:
        return 0


def _playwright_browser() -> str | None:
    roots = [Path(os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "/nonexistent")), Path.home() / ".cache" / "ms-playwright", Path("/opt/pw-browsers")]
    pats = ["chromium_headless_shell-*/chrome-linux/headless_shell", "chromium_headless_shell-*/chrome-linux64/headless_shell",
            "chromium-*/chrome-linux/chrome", "chromium-*/chrome-linux64/chrome"]
    for r in roots:
        for p in pats:
            hits = sorted(r.glob(p), reverse=True)
            if hits:
                return str(hits[0])
    return None


def find_browser() -> str | None:
    """SF_BROWSER → modern Chrome recorded by `setup` → Playwright's Chromium → None (Remotion downloads its own)."""
    if os.environ.get("SF_BROWSER"):
        return os.environ["SF_BROWSER"]
    if BROWSER_JSON.exists():
        p = json.loads(BROWSER_JSON.read_text()).get("path")
        if p and Path(p).exists():
            return p
    return _playwright_browser()


def ensure_modern_browser(rt: Path) -> str | None:
    """Chrome ≥149 for HTML-in-canvas. 1) Remotion's own download (normal networks) 2) npm @sparticuz/chromium (x64 Linux,
    works where only the npm registry is reachable). Recorded in ~/.cache/slide-forge/browser.json."""
    cur = find_browser()
    npm_copy_ok = cur is None or "chrome149" not in str(cur) or (Path(cur).parent / "libGLESv2.so").exists()
    if chrome_major(cur) >= MODERN_CHROME and npm_copy_ok:
        return cur
    js = "require('@remotion/renderer').ensureBrowser({logLevel:'error'}).then(s=>console.log(JSON.stringify(s))).catch(e=>{console.log(JSON.stringify({type:'error',msg:String(e)}));})"
    try:
        r = subprocess.run(["node", "-e", js], cwd=rt, capture_output=True, text=True, timeout=600)
        st = json.loads((r.stdout.strip().splitlines() or ["{}"])[-1])
        if st.get("path") and chrome_major(st["path"]) >= MODERN_CHROME:
            BROWSER_JSON.write_text(json.dumps({"path": st["path"], "source": "remotion"}))
            return st["path"]
    except Exception:
        pass
    import platform
    if platform.system() == "Linux" and platform.machine() in ("x86_64", "AMD64"):
        d = CACHE / "chromium-npm"; d.mkdir(parents=True, exist_ok=True)
        if not (d / "package.json").exists():
            (d / "package.json").write_text('{"private":true}')
        print("  fetching Chrome 149 via npm (@sparticuz/chromium) …")
        if subprocess.run(["npm", "install", "--no-audit", "--no-fund", "--loglevel=error", "@sparticuz/chromium@149.0.0"], cwd=d).returncode == 0:
            r = subprocess.run(["node", "-e", "(m=>(m.default||m))(require('@sparticuz/chromium')).executablePath().then(p=>console.log(p))"], cwd=d, capture_output=True, text=True, timeout=600)
            src = Path((r.stdout.strip().splitlines() or [""])[-1])
            if src.exists():
                dst = CACHE / "chrome149"; dst.mkdir(exist_ok=True)
                # chromium needs its GL stack (ANGLE libEGL/libGLESv2 + SwiftShader Vulkan) and locales beside it
                for name in ("chromium", "libEGL.so", "libGLESv2.so", "libvk_swiftshader.so", "libvulkan.so.1", "vk_swiftshader_icd.json", "locales"):
                    f = src.parent / name
                    if f.is_dir():
                        shutil.copytree(f, dst / name, dirs_exist_ok=True)
                    elif f.exists():
                        shutil.copy2(f, dst / name)
                exe = dst / "chromium"; exe.chmod(0o755)
                if chrome_major(str(exe)) >= MODERN_CHROME:
                    BROWSER_JSON.write_text(json.dumps({"path": str(exe), "source": "npm:@sparticuz/chromium@149"}))
                    return str(exe)
    return None


def node_env() -> dict:
    env = dict(os.environ)
    b = find_browser()
    if b:
        env["SF_BROWSER"] = b
    env.setdefault("SF_GL", "swangle")   # software GL: works headless & in containers without a GPU
    return env


def run_node(proj: Path, *args: str) -> None:
    link_runtime(proj)
    r = subprocess.run(["node", "render.mjs", *args], cwd=proj, env=node_env())
    if r.returncode != 0:
        die(f"render.mjs {args[0]} failed")


# ------------------------------------------------------------------ storyboard
def load_sb(proj: Path) -> dict:
    p = proj / "storyboard.json"
    if not p.exists():
        die(f"{p} がありません。`video.py new {proj}` で作成してください。")
    return json.loads(p.read_text(encoding="utf-8"))


def frames(sb, s):
    return round(s * sb["fps"])


def transition_into(sb, i: int) -> dict:
    """Transition INTO scene i: scene override → storyboard default → motion-preset default (same rule as Movie.tsx)."""
    base = dict(DEFAULTS["transition"].get(sb.get("motion", "calm"), DEFAULTS["transition"]["calm"]))
    base.update(sb.get("transition") or {}); base.update(sb["scenes"][i].get("transition") or {})
    return base


def overlap_into(sb, i: int) -> int:
    if i == 0 or sb["scenes"][i].get("overlay"):
        return 0
    t = transition_into(sb, i)
    return 0 if t.get("type") == "none" else frames(sb, t.get("seconds", 0.5))


def timeline(sb) -> list[tuple[int, int]]:
    """(start, length) in frames for each scene, accounting for transition overlap."""
    out, t = [], 0
    for i, s in enumerate(sb["scenes"]):
        t -= overlap_into(sb, i)
        n = frames(sb, s["seconds"]); out.append((t, n)); t += n
    return out


def duration(sb) -> int:
    tl = timeline(sb)
    return tl[-1][0] + tl[-1][1] if tl else 0


PATH_KEYS = {"texture", "image", "backdrop", "lottie", "type", "effect", "by", "align", "side", "viz", "direction", "timing"}


def all_text(sb) -> str:
    """Every visible string in the storyboard (for font subsetting)."""
    acc: list[str] = [sb.get("title", "")]
    def walk(v, key=""):
        if isinstance(v, str):
            if key not in PATH_KEYS: acc.append(v)
        elif isinstance(v, dict):
            for k, x in v.items(): walk(x, k)
        elif isinstance(v, list):
            for x in v: walk(x, key)
        elif isinstance(v, (int, float)) and key in ("value",):
            acc.append(str(v))
    walk(sb["scenes"])
    return "".join(acc) + "0123456789,.%"


def theme_style(theme: str) -> tuple[dict, list[str], list[str]]:
    css_path = THEMES / f"{theme}.css"
    if not css_path.exists():
        die(f"theme '{theme}' not found (have: {', '.join(p.stem for p in THEMES.glob('*.css'))})")
    css = css_path.read_text(encoding="utf-8")
    root = re.search(r":root\s*{([^}]*)}", css).group(1)
    var = lambda k, d="": (re.search(rf"--{k}:\s*([^;]+);", root) or [None, d])[1].strip()
    import fonts as F
    specs = F.parse_theme_fonts(css)
    acc = var("accent", "#F2B33D")
    r, g, b = (int(acc.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)) if re.fullmatch(r"#[0-9a-fA-F]{6}", acc) else (242, 179, 61)
    style = {
        "bg": var("bg", "#0C1422"), "fg": var("fg", "#EDE7DA"), "muted": var("muted", "#9AA0AD"), "accent": acc, "accent2": var("accent-2", acc),
        "glow": f"rgba({r},{g},{b},.10)",
        "head": var("font-head", "sans-serif"), "body": var("font-body", "sans-serif"),
        "num": var("font-num", var("font-head", "sans-serif")), "mono": var("font-mono", "monospace"),
    }
    scheme = (re.search(r"@scheme\s+(\w+)", css) or [None, "dark"])[1]
    return style, [s.family for s in specs], [scheme]


# ------------------------------------------------------------------ commands
def cmd_setup(a):
    rt = ensure_runtime()
    print(f"✓ runtime ready: {rt}")
    b = None if a.no_modern else ensure_modern_browser(rt)
    b = b or find_browser()
    v = chrome_major(b)
    print(f"  browser: {b or '(none — Remotion will download chrome-headless-shell on first render)'}" + (f"  (Chrome {v})" if v else ""))
    if v and v < MODERN_CHROME:
        print(f"  ⚠ Chrome {v} < {MODERN_CHROME}: shader transitions ({', '.join(sorted(SHADER)[:4])}…) and motionBlur are unavailable; CSS transitions & everything else work")


def cmd_new(a):
    proj = Path(a.dir)
    if proj.exists() and any(proj.iterdir()) and not a.force:
        die(f"{proj} は空ではありません（--force で上書き）")
    proj.mkdir(parents=True, exist_ok=True)
    for name in TEMPLATE_FILES:
        src, dst = TEMPLATE / name, proj / name
        if src.is_dir():
            shutil.copytree(src, dst, dirs_exist_ok=True)
        else:
            shutil.copy2(src, dst)
    (proj / "public" / "media").mkdir(parents=True, exist_ok=True)
    example = TEMPLATE / ("storyboard.motion.json" if a.example == "motion" else "storyboard.example.json")
    sb = json.loads(Path(a.storyboard).read_text(encoding="utf-8")) if a.storyboard else json.loads(example.read_text(encoding="utf-8"))
    if a.motion:
        sb["motion"] = a.motion
    if a.theme or "style" not in sb:
        style, fams, _ = theme_style(a.theme or "signal")
        sb["style"], sb["fonts"], sb["theme"] = style, fams, a.theme or "signal"
    (proj / "storyboard.json").write_text(json.dumps(sb, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    gi = proj / ".gitignore"; gi.write_text("node_modules\nout\n")
    print(f"✓ {proj}/ created ({len(sb['scenes'])} scenes, theme {sb.get('theme', '-')})")
    print("  next: put images with `video.py add`, edit storyboard.json, then `video.py check` → `stills` → `render`")


def _credit_for(src: Path) -> dict | None:
    side = src.with_name(src.name + ".json")
    if side.exists():
        return json.loads(side.read_text(encoding="utf-8"))
    for led in (src.parent / "credits.json", src.parent.parent / "credits.json"):
        if led.exists():
            cr = json.loads(led.read_text(encoding="utf-8"))
            for k, v in cr.items():
                if Path(k).name == src.name:
                    return v
    return None


def cmd_add(a):
    proj = Path(a.dir).resolve(); media = proj / "public" / "media"; media.mkdir(parents=True, exist_ok=True)
    led_path = proj / "credits.json"
    led = json.loads(led_path.read_text(encoding="utf-8")) if led_path.exists() else {}
    for i, f in enumerate(a.files):
        src = Path(f)
        if not src.exists():
            die(f"{src} not found")
        name = a.as_ if (a.as_ and len(a.files) == 1) else src.name
        dst = media / name
        shutil.copy2(src, dst)
        key = f"media/{name}"
        cr = _credit_for(src)
        if a.own:
            cr = {"license": "own", "creator": a.own, "source": "provided by user"}
        elif a.license:
            cr = {"license": a.license, "creator": a.creator or "", "source": a.source or ""}
        if cr:
            led[key] = cr
            print(f"✓ {key}  [{cr.get('license', '?')}] {cr.get('creator', '')}")
        else:
            print(f"⚠ {key}  licence unknown — add a sidecar {src.name}.json, --license/--creator/--source, --own \"<owner>\", or don't use it")
    led_path.write_text(json.dumps(led, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _units(text: str) -> int:
    """rough count of animated units (phrases) for build-time estimates"""
    t = re.sub(r"\*\*|==|__|\(\(|\)\)", "", text)
    jp = sum(1 for c in t if ord(c) > 0x2E80); lat = len(re.findall(r"[A-Za-z0-9]+", t))
    return max(1, round(jp / 3.2) + lat)


def check(proj: Path, quiet=False) -> int:
    sb = load_sb(proj); errs, warns = [], []
    for k in ("fps", "width", "height", "scenes", "style"):
        if k not in sb:
            errs.append(f"storyboard: missing '{k}'")
    if errs:
        for e in errs: print("✗", e)
        return len(errs)
    led = json.loads((proj / "credits.json").read_text(encoding="utf-8")) if (proj / "credits.json").exists() else {}
    pub = proj / "public"
    fps = sb["fps"]
    if sb.get("motion", "calm") not in PRESETS:
        errs.append(f"motion: '{sb.get('motion')}' (use {', '.join(sorted(PRESETS))})")
    if sb.get("sky") and not (pub / sb["sky"]).exists():
        errs.append(f"sky: public/{sb['sky']} not found")
    modern = chrome_major(find_browser()) >= MODERN_CHROME
    kinds = []
    for i, s in enumerate(sb["scenes"], 1):
        t = s.get("type"); tag = f"scene {i} ({t})"
        if t not in SCENE_TYPES:
            errs.append(f"{tag}: unknown type (use {', '.join(sorted(SCENE_TYPES))})"); continue
        main_text = s.get("text") if t == "kinetic" else s.get("title")
        if not main_text:
            errs.append(f"{tag}: {'text' if t == 'kinetic' else 'title'} is required")
        if not isinstance(s.get("seconds"), (int, float)) or s["seconds"] < 1.5:
            errs.append(f"{tag}: seconds must be ≥ 1.5")
        # transitions / overlays
        if i > 1:
            tr = transition_into(sb, i - 1)
            if s.get("overlay"):
                kinds.append("lightLeak")
                if s["overlay"].get("type", "lightLeak") != "lightLeak":
                    errs.append(f"{tag}: overlay.type must be lightLeak")
            else:
                ty = tr.get("type")
                kinds.append(ty)
                if ty not in CSS_TRANSITIONS | SHADER:
                    errs.append(f"{tag}: transition '{ty}' unknown (CSS: {', '.join(sorted(CSS_TRANSITIONS))}; shader: {', '.join(sorted(SHADER))})")
                elif ty in SHADER and not modern:
                    errs.append(f"{tag}: '{ty}' needs Chrome ≥{MODERN_CHROME} (run `video.py setup`), or use a CSS transition")
                sec = tr.get("seconds", 0.5)
                if ty != "none" and not (0.2 <= sec <= 1.5):
                    warns.append(f"{tag}: transition {sec}s — keep 0.3–1.0 s (short = energy, long = calm)")
                if ty != "none" and frames(sb, sec) * 2 > frames(sb, s.get("seconds", 3)):
                    warns.append(f"{tag}: transition eats over half the scene")
        if s.get("motionBlur"):
            if t == "globe": errs.append(f"{tag}: motionBlur is not supported on 3D scenes")
            elif not modern: errs.append(f"{tag}: motionBlur needs Chrome ≥{MODERN_CHROME} (run `video.py setup`)")
            else: warns.append(f"{tag}: motionBlur is experimental — 6× render cost, and semi-transparent layers (glows, markers) come out too strong in Remotion 4.0.529; check the stills")
        if s.get("effect") and s["effect"] not in EFFECTS:
            errs.append(f"{tag}: effect '{s['effect']}' (use {', '.join(sorted(EFFECTS))})")
        # media
        media = [s.get("texture"), s.get("image"), s.get("lottie")] + ([s["backdrop"]] if s.get("backdrop") not in (None, "stars", "plain", "mesh", "grid", "dots", "rays") else [])
        for m in filter(None, media):
            if not (pub / m).exists():
                errs.append(f"{tag}: public/{m} not found")
            elif m.startswith("media/") and m not in led:
                warns.append(f"{tag}: {m} has no credits.json entry (licence unknown)")
            if not s.get("credit"):
                warns.append(f"{tag}: uses {m} but has no on-screen 'credit'")
        need_key = {"globe": "texture", "photo": "image", "lottie": "lottie", "stat": "big"}.get(t)
        if need_key and not s.get(need_key):
            errs.append(f"{tag}: {need_key} is required")
        if t in ("steps", "bars"):
            items = s.get("items") or []
            lo, hi = (2, 5) if t == "steps" else (2, 7)
            if not (lo <= len(items) <= hi):
                errs.append(f"{tag}: items must have {lo}–{hi} entries (has {len(items)})")
            if t == "bars" and any(not isinstance(it.get("value"), (int, float)) for it in items):
                errs.append(f"{tag}: every bar needs a numeric value")
            if t == "bars" and not s.get("credit"):
                warns.append(f"{tag}: data without a source — add 'credit' (出典)")
            if t == "steps" and any(len(it.get("title", "")) > 12 for it in items):
                warns.append(f"{tag}: step titles over 12 chars wrap awkwardly — shorten")
        if t == "stat" and s.get("viz") in ("ring", "bar") and s.get("value") is None and s.get("unit") != "%":
            warns.append(f"{tag}: ring/bar needs 'value' (0–100) unless unit is %")
        # text size / reading time
        if t == "kinetic":
            lines = str(s.get("text", "")).split("\n")
            if len(lines) > 3: warns.append(f"{tag}: {len(lines)} lines — kinetic statements read best in 1–3 lines")
            if max(len(re.sub(r"\*\*|==|__|\(\(|\)\)", "", l)) for l in lines) > 16:
                warns.append(f"{tag}: a line over 16 chars shrinks the type — break it with \\n")
        else:
            title = s.get("title", "")
            if len(title) > TITLE_MAX[t]:
                warns.append(f"{tag}: title {len(title)} chars > {TITLE_MAX[t]} — shorten (one claim per scene)")
        if s.get("big") and len(str(s["big"])) + len(str(s.get("unit", ""))) > 9:
            warns.append(f"{tag}: big number '{s['big']}{s.get('unit', '')}' too long — shorten the unit")
        txt = "".join(str(s.get(k, "")) for k in ("title", "text", "sub", "caption"))
        txt += "".join(str(it.get("title", "")) + str(it.get("text", "")) + str(it.get("label", "")) for it in (s.get("items") or []))
        chars = round(sum(0.3 if ord(c) < 0x2E80 else 1 for c in re.sub(r"\*\*|==|__|\(\(|\)\)", "", txt)))
        stagger = {"calm": 5, "lively": 4, "punchy": 3}[sb.get("motion", "calm") if sb.get("motion", "calm") in PRESETS else "calm"]
        build = (_units(str(main_text or "")) * stagger + 20) / 30          # seconds until the headline has settled
        if t in ("steps", "bars"): build += len(s.get("items") or []) * 0.35
        need = max(build, chars / READ_CPS) + 0.8                             # reading overlaps the build; ≥0.5 s hold after settle + exit
        if isinstance(s.get("seconds"), (int, float)) and s["seconds"] < need:
            warns.append(f"{tag}: needs ≈{need:.1f}s (build {build:.1f}s / read {chars / READ_CPS:.1f}s, + hold), scene is {s['seconds']}s")
    distinct = sorted(set(k for k in kinds if k != "none"))
    if len(distinct) > 3:
        warns.append(f"{len(distinct)} different transitions ({', '.join(distinct)}) — pick 1–2 and a rule for when each is used")
    total = duration(sb) / fps
    if not quiet:
        for e in errs: print("✗", e)
        for w in warns: print("⚠", w)
        print(f"{'✓' if not errs else '✗'} {len(sb['scenes'])} scenes · {total:.1f}s · motion {sb.get('motion', 'calm')} · {len(errs)} errors, {len(warns)} warnings")
    return len(errs)


def cmd_check(a):
    sys.exit(1 if check(Path(a.dir).resolve()) else 0)


def make_fonts(proj: Path, force=False):
    out = proj / "public" / "fonts.css"
    sb = load_sb(proj)
    stamp = hashlib.sha1((all_text(sb) + json.dumps(sb.get("fonts", []))).encode()).hexdigest()[:12]
    if out.exists() and not force and stamp in out.read_text(encoding="utf-8")[:200]:
        return
    import fonts as F
    specs = []
    theme_css = THEMES / f"{sb.get('theme', '')}.css"
    if theme_css.exists():
        specs = [s for s in F.parse_theme_fonts(theme_css.read_text(encoding="utf-8")) if s.family in sb.get("fonts", [])]
    have = {s.family for s in specs}
    specs += [F.FontSpec(f, ["400", "700"]) for f in sb.get("fonts", []) if f not in have]
    css = F.embed_css(specs, all_text(sb), log=lambda m: print(m)) if specs else ""
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(f"/* sf-fonts {stamp} */\n{css}", encoding="utf-8")
    print(f"  fonts.css: {out.stat().st_size // 1024} KB")


def cmd_fonts(a):
    make_fonts(Path(a.dir).resolve(), force=True)


def prepare(proj: Path):
    if check(proj):
        die("fix the errors above first")
    make_fonts(proj)


def sheet(images: list[Path], out: Path, cols=4, width=480, labels: list[str] | None = None):
    from PIL import Image, ImageDraw
    ims = [Image.open(p).convert("RGB") for p in images]
    if not ims:
        die(f"no frames were rendered for {out.name} (see errors above)")
    h = int(width * ims[0].height / ims[0].width)
    rows = (len(ims) + cols - 1) // cols
    S = Image.new("RGB", (cols * width + (cols + 1) * 8, rows * (h + 8) + 8), "#222")
    d = ImageDraw.Draw(S)
    for i, im in enumerate(ims):
        x, y = 8 + (i % cols) * (width + 8), 8 + (i // cols) * (h + 8)
        S.paste(im.resize((width, h)), (x, y))
        if labels:
            d.rectangle([x, y, x + 64, y + 20], fill="#000"); d.text((x + 4, y + 4), labels[i], fill="#fff")
    S.save(out)


def cmd_stills(a):
    proj = Path(a.dir).resolve(); prepare(proj); sb = load_sb(proj)
    tl = timeline(sb)
    # one frame per scene, late enough that entrances & count-ups have finished, before the fade-out
    fr = [min(st + n - 1, st + max(int(sb["fps"] * 2.2), int(n * 0.72))) for st, n in tl]
    outdir = proj / "out" / "stills"
    if outdir.exists():
        shutil.rmtree(outdir)
    run_node(proj, "stills", "--frames", ",".join(map(str, fr)), "--outdir", str(outdir), "--scale", str(a.scale))
    imgs = sorted(outdir.glob("f*.png"))
    sheet(imgs, proj / "out" / "sheet.png", labels=[f"#{i + 1} {f}" for i, f in enumerate(fr)])
    print(f"✓ {proj / 'out' / 'sheet.png'}  ← Read it: layout, legibility, crop, text wraps")


def cmd_det(a):
    proj = Path(a.dir).resolve(); prepare(proj); sb = load_sb(proj)
    f = a.frame if a.frame is not None else int(duration(sb) * 0.4)
    outdir = proj / "out" / "det"
    run_node(proj, "det", "--frame", str(f), "--outdir", str(outdir), "--scale", "0.5")
    from PIL import Image, ImageChops
    x, y = (Image.open(outdir / f"det-{i}.png").convert("RGB") for i in (1, 2))
    diff = ImageChops.difference(x, y).getbbox()
    if diff:
        die(f"frame {f} differs between renders (bbox {diff}) — something uses time/Math.random/useFrame; see references/video.md §2")
    print(f"✓ deterministic: frame {f} identical across renders")


def cmd_motion(a):
    proj = Path(a.dir).resolve(); prepare(proj); sb = load_sb(proj)
    tl = timeline(sb)
    if not 1 <= a.scene <= len(tl):
        die(f"--scene must be 1..{len(tl)}")
    st, n = tl[a.scene - 1]
    fr = sorted({st + round(k * (n - 1) / (a.n - 1)) for k in range(a.n)})
    outdir = proj / "out" / f"motion-{a.scene:02d}"
    if outdir.exists():
        shutil.rmtree(outdir)
    run_node(proj, "stills", "--frames", ",".join(map(str, fr)), "--outdir", str(outdir), "--scale", "0.35")
    imgs = sorted(outdir.glob("f*.png"))
    out = proj / "out" / f"motion-{a.scene:02d}.png"
    sheet(imgs, out, cols=6, width=360, labels=[f"{(f - st) / sb['fps']:.2f}s" for f in fr])
    print(f"✓ {out}  ← Read it: order of entrances, overshoot, when the text settles, exit/transition overlap")


def flash_check(mp4: Path, fps_hint: int = 30) -> tuple[int, list[str]]:
    """General-flash approximation of WCAG 2.3.1: count opposing luminance swings ≥10% (darker side <0.8)
    in the full frame and each quadrant; more than 3 flashes (6 transitions) inside any 1 s window fails."""
    if not shutil.which("ffmpeg"):
        return 0, ["ffmpeg not found — flash check skipped"]
    W, H = 64, 36
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(mp4), "-vf", f"scale={W}:{H},format=gray", "-f", "rawvideo", "-"], capture_output=True).stdout
    n = len(raw) // (W * H)
    if n < 2:
        return 0, []
    import statistics
    def lum(v): v /= 255; return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
    regions = {"frame": (0, 0, W, H), "TL": (0, 0, W // 2, H // 2), "TR": (W // 2, 0, W, H // 2), "BL": (0, H // 2, W // 2, H), "BR": (W // 2, H // 2, W, H)}
    worst, notes = 0, []
    for name, (x0, y0, x1, y1) in regions.items():
        L = []
        for i in range(n):
            base = i * W * H
            vals = [raw[base + y * W + x] for y in range(y0, y1, 2) for x in range(x0, x1, 2)]
            L.append(lum(statistics.fmean(vals)))
        events, last_dir, ref = [], 0, L[0]
        for i in range(1, n):
            d = L[i] - ref
            if abs(d) >= 0.1 and min(L[i], ref) < 0.8:
                dr = 1 if d > 0 else -1
                if dr != last_dir:
                    events.append(i); last_dir = dr
                ref = L[i]
            elif (d > 0) == (last_dir > 0):
                ref = L[i] if abs(L[i] - ref) > 0 else ref
        # flashes in any 1 s window = transitions / 2
        j = 0
        for k in range(len(events)):
            while events[k] - events[j] >= fps_hint: j += 1
            fl = (k - j + 1) // 2
            if fl > worst: worst = fl
            if fl > 3: notes.append(f"{name}: {fl} flashes around {events[k] / fps_hint:.1f}s")
    return worst, sorted(set(notes))[:6]


def cmd_flash(a):
    worst, notes = flash_check(Path(a.file), a.fps)
    for x in notes: print("✗", x)
    print(f"{'✓' if worst <= 3 else '✗'} max {worst} flashes in any 1 s (limit 3)")
    sys.exit(0 if worst <= 3 else 1)


def cmd_render(a):
    proj = Path(a.dir).resolve(); prepare(proj); sb = load_sb(proj)
    name = re.sub(r"[^\w.-]+", "-", a.out or "movie.mp4")
    out = (proj / "out" / name) if not a.out or "/" not in a.out else Path(a.out)
    cores = os.cpu_count() or 2
    conc = a.concurrency or max(1, min(cores, 8))
    args = ["video", "--out", str(out.resolve()), "--concurrency", str(conc)]
    if a.draft:
        args += ["--scale", "0.5", "--crf", "28"]
    else:
        args += ["--crf", str(a.crf)]
    print(f"  rendering {duration(sb)} frames ({duration(sb) / sb['fps']:.1f}s) · concurrency {conc}{' · draft ½ scale' if a.draft else ''}")
    run_node(proj, *args)
    if shutil.which("ffmpeg"):
        sh = out.with_name(out.stem + "-sheet.png")
        n = duration(sb); step = max(1, n // 24)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(out), "-vf", f"select='not(mod(n\\,{step}))',scale=480:-1,tile=6x4", "-frames:v", "1", str(sh)])
        if shutil.which("ffprobe"):
            d = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(out)], capture_output=True, text=True).stdout.strip()
            print(f"  duration {d}s · {out.stat().st_size / 1e6:.1f} MB")
        worst, notes = flash_check(out, sb["fps"])
        for x in notes: print("  ✗ flash:", x)
        print(f"  flash check: max {worst}/s {'✓' if worst <= 3 else '✗ — slow down the strobe/flicker (WCAG 2.3.1)'}")
        print(f"✓ {out}\n  contact sheet: {sh}  ← Read it")
    else:
        print(f"✓ {out}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("setup"); p.add_argument("--no-modern", action="store_true", help="skip fetching Chrome ≥149"); p.set_defaults(fn=cmd_setup)
    p = sp.add_parser("new"); p.add_argument("dir"); p.add_argument("--theme"); p.add_argument("--storyboard"); p.add_argument("--example", choices=["solar", "motion"], default="solar", help="starting storyboard when --storyboard is not given"); p.add_argument("--motion", choices=sorted(PRESETS)); p.add_argument("--force", action="store_true"); p.set_defaults(fn=cmd_new)
    p = sp.add_parser("add"); p.add_argument("dir"); p.add_argument("files", nargs="+"); p.add_argument("--as", dest="as_"); p.add_argument("--own", metavar="OWNER", help="user-provided material: record owner")
    p.add_argument("--license", help="licence you verified on the source page, e.g. CC0, CC-BY-4.0, MIT"); p.add_argument("--creator"); p.add_argument("--source", help="page URL where the licence is stated")
    p.set_defaults(fn=cmd_add)
    p = sp.add_parser("check"); p.add_argument("dir"); p.set_defaults(fn=cmd_check)
    p = sp.add_parser("fonts"); p.add_argument("dir"); p.set_defaults(fn=cmd_fonts)
    p = sp.add_parser("stills"); p.add_argument("dir"); p.add_argument("--scale", type=float, default=0.5); p.set_defaults(fn=cmd_stills)
    p = sp.add_parser("det"); p.add_argument("dir"); p.add_argument("--frame", type=int); p.set_defaults(fn=cmd_det)
    p = sp.add_parser("motion"); p.add_argument("dir"); p.add_argument("--scene", type=int, required=True); p.add_argument("--n", type=int, default=12); p.set_defaults(fn=cmd_motion)
    p = sp.add_parser("flash"); p.add_argument("file"); p.add_argument("--fps", type=int, default=30); p.set_defaults(fn=cmd_flash)
    p = sp.add_parser("render"); p.add_argument("dir"); p.add_argument("--out"); p.add_argument("--draft", action="store_true")
    p.add_argument("--crf", type=int, default=18); p.add_argument("--concurrency", type=int); p.set_defaults(fn=cmd_render)
    a = ap.parse_args(); a.fn(a)


if __name__ == "__main__":
    main()
