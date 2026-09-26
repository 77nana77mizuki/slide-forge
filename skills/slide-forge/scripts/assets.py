#!/usr/bin/env python3
"""Find, pick, process and license-track images & icons for a Slide Forge deck.

Run from the deck's folder (where deck.src.html lives). Everything is recorded in ./credits.json,
which build.py uses to add credit captions / a credits slide and to flag unlicensed images.

  SEARCH  (writes numbered candidates + a contact sheet you should LOOK at before picking)
    assets.py search "team meeting modern office" --kind photo --orientation landscape
    assets.py search "工場 ロボット" --sources pixabay --kind illustration
    assets.py search "server room" --sources local:~/company-photos

  PICK    (download full size, crop/resize/treat, record the licence)
    assets.py pick img/_cand/team-meeting-modern-office 3 --as img/team.jpg --crop 16:9
    assets.py pick img/_cand/server-room 1 --as img/bg.jpg --crop 16:9 --treat duotone --theme signal

  ICONS   (open-source SVG icon sets; normally just write <i class="ico" data-icon="tabler:rocket"></i>
           in the deck and build.py resolves it — use this to browse/choose)
    assets.py icon rocket shield "user check" --sets tabler,lucide,ph --sheet

  RECORD  (images you already have)
    assets.py add img/own-photo.jpg --own
    assets.py fetch https://example.org/a.jpg --as img/a.jpg --license "CC BY 4.0" \
        --creator "Name" --source-url https://example.org/page --title "…"

  REPORT
    assets.py credits [deck.src.html]        # used images, licences, missing records

Sources (default: every source that works without a key, plus keyed ones whose env var is set):
  nasa        NASA Image and Video Library – space, missions, Earth (no key; credit NASA, no logos/endorsement)
  openverse   CC-licensed images from many providers (no key)
  wikimedia   Wikimedia Commons (no key; great for places, objects, history)
  pixabay     PIXABAY_API_KEY  – photos/illustrations/vectors, Japanese queries OK (lang=ja)
  unsplash    UNSPLASH_ACCESS_KEY – high-quality photos (credit shown automatically)
  pexels      PEXELS_API_KEY   – high-quality photos
  local:DIR   your own/company library; optional sidecar DIR/<file>.json {"license":…, "creator":…}

Licence policy: NC (non-commercial) and ND (no-derivatives) results are excluded unless
--allow-nc / --allow-nd. ND images cannot be cropped or colour-treated.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import datetime as dt
import hashlib
import html
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
THEMES = HERE.parent / "assets" / "themes"
CACHE = Path(os.environ.get("SLIDE_FORGE_CACHE", Path.home() / ".cache" / "slide-forge"))
UA = "SlideForge/1.1 (presentation asset search; +https://github.com/) python-urllib"
TIMEOUT = 25             # s — image hosts can be slow; generous but bounded
PER_SOURCE = 12          # candidates per source; enough choice, sheet stays readable
MIN_WIDTH = 1000         # px — below this a photo looks soft even in a half-slide frame
IMG_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif"}
DEFAULT_ICON_SETS = ["tabler", "lucide", "ph", "material-symbols"]

# ------------------------------------------------------------------ licences
LICENSES = {
    # code: (display, url, attribution_required, commercial_ok, derivatives_ok, share_alike)
    "cc0": ("CC0 1.0", "https://creativecommons.org/publicdomain/zero/1.0/", False, True, True, False),
    "pdm": ("Public Domain Mark", "https://creativecommons.org/publicdomain/mark/1.0/", False, True, True, False),
    "by": ("CC BY", "https://creativecommons.org/licenses/by/{v}/", True, True, True, False),
    "by-sa": ("CC BY-SA", "https://creativecommons.org/licenses/by-sa/{v}/", True, True, True, True),
    "by-nd": ("CC BY-ND", "https://creativecommons.org/licenses/by-nd/{v}/", True, True, False, False),
    "by-nc": ("CC BY-NC", "https://creativecommons.org/licenses/by-nc/{v}/", True, False, True, False),
    "by-nc-sa": ("CC BY-NC-SA", "https://creativecommons.org/licenses/by-nc-sa/{v}/", True, False, True, True),
    "by-nc-nd": ("CC BY-NC-ND", "https://creativecommons.org/licenses/by-nc-nd/{v}/", True, False, False, False),
    "unsplash": ("Unsplash License", "https://unsplash.com/license", False, True, True, False),
    "pexels": ("Pexels License", "https://www.pexels.com/license/", False, True, True, False),
    "pixabay": ("Pixabay Content License", "https://pixabay.com/service/license-summary/", False, True, True, False),
    "nasa": ("NASA (no copyright; credit NASA)", "https://www.nasa.gov/nasa-brand-center/images-and-media/", False, True, True, False),
    "own": ("Own / provided by the user", "", False, True, True, False),
}


def lic_info(code: str, version: str = "4.0") -> dict:
    code = (code or "").lower().strip()
    if code not in LICENSES:
        return {"license": code or "unknown", "license_url": "", "attribution_required": True,
                "commercial_ok": False, "derivatives_ok": False, "share_alike": False}
    name, url, attr, com, der, sa = LICENSES[code]
    v = version or "4.0"
    return {"license": f"{name} {v}".strip() if code.startswith("by") else name,
            "license_url": url.format(v=v), "attribution_required": attr, "commercial_ok": com,
            "derivatives_ok": der, "share_alike": sa}


def parse_license_text(text: str) -> tuple[str, str]:
    """'CC BY-SA 4.0' / 'Public domain' / 'CC0' → (code, version)."""
    t = (text or "").lower().replace("attribution", "by").replace("sharealike", "sa").replace("noncommercial", "nc")
    if "cc0" in t or "zero" in t:
        return "cc0", "1.0"
    if "public domain" in t or t.strip() in ("pd", "pdm"):
        return "pdm", ""
    m = re.search(r"cc[\s-]*(by(?:[\s-]*(?:nc|sa|nd))*)[\s-]*([\d.]+)?", t)
    if m:
        return re.sub(r"[\s]+", "-", m.group(1)).replace("--", "-"), (m.group(2) or "4.0")
    for k in ("unsplash", "pexels", "pixabay", "nasa", "own"):
        if k in t:
            return k, ""
    return t.strip() or "unknown", ""


# ------------------------------------------------------------------ http
def http(url: str, headers: dict | None = None, binary=False, timeout=TIMEOUT):
    req = urllib.request.Request(url, headers={"User-Agent": UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = r.read()
    return data if binary else json.loads(data.decode("utf-8"))


def slugify(s: str) -> str:
    s = re.sub(r"[^\w\u3040-\u30ff\u3400-\u9fff]+", "-", s.lower()).strip("-")
    return s[:48] or hashlib.md5(s.encode()).hexdigest()[:8]


def has_cjk(s: str) -> bool:
    return bool(re.search(r"[\u3040-\u30ff\u3400-\u9fff]", s))


def strip_html(s: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", s or "")).strip()


# ------------------------------------------------------------------ sources → normalised candidates
# candidate = {source, id, title, thumb, full, width, height, page, creator, creator_url, license_code, license_version, extra}

def src_openverse(q, kind, orient, n):
    p = {"q": q, "page_size": min(20, n), "mature": "false", "license_type": "commercial,modification"}
    if kind in ("photo", "illustration"):
        p["category"] = "photograph" if kind == "photo" else "illustration,digitized_artwork"
    if orient:
        p["aspect_ratio"] = {"landscape": "wide", "portrait": "tall", "square": "square"}[orient]
    d = http("https://api.openverse.org/v1/images/?" + urllib.parse.urlencode(p))
    out = []
    for r in d.get("results", []):
        out.append({"source": f"Openverse/{r.get('source') or r.get('provider')}", "id": r["id"], "title": r.get("title") or "",
                    "thumb": r.get("thumbnail") or r["url"], "full": r["url"], "width": r.get("width") or 0, "height": r.get("height") or 0,
                    "page": r.get("foreign_landing_url") or "", "creator": r.get("creator") or "", "creator_url": r.get("creator_url") or "",
                    "license_code": r.get("license") or "", "license_version": r.get("license_version") or "", "extra": {}})
    return out


def src_wikimedia(q, kind, orient, n):
    p = {"action": "query", "format": "json", "generator": "search", "gsrsearch": f"{q} filetype:bitmap", "gsrnamespace": 6,
         "gsrlimit": min(30, n * 2), "prop": "imageinfo", "iiprop": "url|size|mime|extmetadata", "iiurlwidth": 480}
    d = http("https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(p))
    out = []
    for pg in sorted(d.get("query", {}).get("pages", {}).values(), key=lambda x: x.get("index", 0)):
        ii = (pg.get("imageinfo") or [{}])[0]
        if not ii or ii.get("mime", "").split("/")[-1] not in ("jpeg", "png", "webp"):
            continue
        em = ii.get("extmetadata", {})
        g = lambda k: strip_html(em.get(k, {}).get("value", ""))  # noqa: E731
        code, ver = parse_license_text(g("LicenseShortName"))
        out.append({"source": "Wikimedia Commons", "id": str(pg.get("pageid")), "title": g("ObjectName") or pg.get("title", "").replace("File:", ""),
                    "thumb": ii.get("thumburl") or ii["url"], "full": ii["url"], "width": ii.get("width", 0), "height": ii.get("height", 0),
                    "page": ii.get("descriptionurl", ""), "creator": g("Artist")[:120], "creator_url": "",
                    "license_code": code, "license_version": ver, "extra": {"usage_terms": g("UsageTerms")}})
    return out[:n]


def src_nasa(q, kind, orient, n):
    """NASA Image and Video Library (no key). NASA media is generally not copyrighted; credit NASA,
    never imply endorsement, never use the NASA insignia/logo. Items marked with a third-party
    copyright in their description are skipped."""
    d = http("https://images-api.nasa.gov/search?" + urllib.parse.urlencode({"q": q, "media_type": "image", "page_size": min(100, n * 2)}))
    out = []
    for it in d.get("collection", {}).get("items", []):
        data = (it.get("data") or [{}])[0]
        links = it.get("links") or []
        if not links:
            continue
        desc = (data.get("description") or "") + " " + (data.get("photographer") or "") + " " + (data.get("secondary_creator") or "")
        if re.search(r"©|copyright|getty|reuters|associated press|\bAP Photo", desc, re.I):
            continue    # third-party material inside NASA's library keeps its own copyright
        thumb = links[0]["href"]
        out.append({"source": f"NASA/{data.get('center', '')}".rstrip("/"), "id": data.get("nasa_id", ""), "title": data.get("title", ""),
                    "thumb": thumb, "full": re.sub(r"~(thumb|small|medium)\.", "~orig.", thumb), "width": 0, "height": 0,
                    "page": f"https://images.nasa.gov/details/{urllib.parse.quote(data.get('nasa_id', ''))}",
                    "creator": data.get("photographer") or data.get("secondary_creator") or "NASA", "creator_url": "",
                    "license_code": "nasa", "license_version": "", "extra": {"date": data.get("date_created", "")}})
        if len(out) >= n:
            break
    return out


def src_pixabay(q, kind, orient, n):
    key = os.environ.get("PIXABAY_API_KEY")
    if not key:
        raise RuntimeError("PIXABAY_API_KEY not set (free key: https://pixabay.com/api/docs/)")
    p = {"key": key, "q": q[:100], "per_page": max(3, min(40, n)), "safesearch": "true", "min_width": MIN_WIDTH,
         "image_type": {"photo": "photo", "illustration": "illustration", "vector": "vector"}.get(kind, "all"),
         "lang": "ja" if has_cjk(q) else "en"}
    if orient in ("landscape", "portrait"):
        p["orientation"] = "horizontal" if orient == "landscape" else "vertical"
    d = http("https://pixabay.com/api/?" + urllib.parse.urlencode(p))
    return [{"source": "Pixabay", "id": str(h["id"]), "title": h.get("tags", ""), "thumb": h.get("webformatURL") or h["previewURL"],
             "full": h.get("largeImageURL") or h["webformatURL"], "width": h.get("imageWidth", 0), "height": h.get("imageHeight", 0),
             "page": h.get("pageURL", ""), "creator": h.get("user", ""), "creator_url": f"https://pixabay.com/users/{h.get('user')}-{h.get('user_id')}/",
             "license_code": "pixabay", "license_version": "", "extra": {}} for h in d.get("hits", [])[:n]]


def src_unsplash(q, kind, orient, n):
    key = os.environ.get("UNSPLASH_ACCESS_KEY")
    if not key:
        raise RuntimeError("UNSPLASH_ACCESS_KEY not set (free key: https://unsplash.com/developers)")
    p = {"query": q, "per_page": min(30, n), "content_filter": "high"}
    if orient:
        p["orientation"] = {"landscape": "landscape", "portrait": "portrait", "square": "squarish"}[orient]
    d = http("https://api.unsplash.com/search/photos?" + urllib.parse.urlencode(p), {"Authorization": f"Client-ID {key}", "Accept-Version": "v1"})
    utm = "?utm_source=slide_forge&utm_medium=referral"
    return [{"source": "Unsplash", "id": r["id"], "title": r.get("alt_description") or r.get("description") or "",
             "thumb": r["urls"]["small"], "full": r["urls"]["raw"] + "&w=2400&q=85&fm=jpg", "width": r.get("width", 0), "height": r.get("height", 0),
             "page": r["links"]["html"] + utm, "creator": r["user"]["name"], "creator_url": r["user"]["links"]["html"] + utm,
             "license_code": "unsplash", "license_version": "", "extra": {"download_location": r["links"].get("download_location")}}
            for r in d.get("results", [])]


def src_pexels(q, kind, orient, n):
    key = os.environ.get("PEXELS_API_KEY")
    if not key:
        raise RuntimeError("PEXELS_API_KEY not set (free key: https://www.pexels.com/api/)")
    p = {"query": q, "per_page": min(40, n), "size": "large"}
    if orient:
        p["orientation"] = orient
    d = http("https://api.pexels.com/v1/search?" + urllib.parse.urlencode(p), {"Authorization": key})
    return [{"source": "Pexels", "id": str(r["id"]), "title": r.get("alt", ""), "thumb": r["src"]["medium"], "full": r["src"]["large2x"],
             "width": r.get("width", 0), "height": r.get("height", 0), "page": r.get("url", ""), "creator": r.get("photographer", ""),
             "creator_url": r.get("photographer_url", ""), "license_code": "pexels", "license_version": "", "extra": {}}
            for r in d.get("photos", [])]


def src_local(q, kind, orient, n, root: Path):
    """Your own / company library. Matches query words against file names and sidecar tags."""
    words = [w for w in re.split(r"\s+", q.lower()) if w]
    out = []
    for f in sorted(root.expanduser().rglob("*")):
        if f.suffix.lower() not in IMG_EXT:
            continue
        side = f.with_suffix(f.suffix + ".json") if f.with_suffix(f.suffix + ".json").exists() else f.with_suffix(".json")
        meta = json.loads(side.read_text(encoding="utf-8")) if side.exists() else {}
        hay = (f.stem + " " + " ".join(meta.get("tags", [])) + " " + meta.get("title", "")).lower()
        score = sum(w in hay for w in words)
        if words and not score:
            continue
        try:
            from PIL import Image
            with Image.open(f) as im:
                w, h = im.size
        except Exception:
            w = h = 0
        code, ver = parse_license_text(meta.get("license", "own"))
        out.append((score, {"source": meta.get("source", "Local library"), "id": str(f), "title": meta.get("title", f.stem), "thumb": str(f), "full": str(f),
                            "width": w, "height": h, "page": meta.get("source_url", ""), "creator": meta.get("creator", ""), "creator_url": meta.get("creator_url", ""),
                            "license_code": code, "license_version": ver, "extra": {}}))
    out.sort(key=lambda x: -x[0])
    return [c for _, c in out[:n]]


SOURCES = {"nasa": src_nasa, "openverse": src_openverse, "wikimedia": src_wikimedia, "pixabay": src_pixabay, "unsplash": src_unsplash, "pexels": src_pexels}
KEYED = {"pixabay": "PIXABAY_API_KEY", "unsplash": "UNSPLASH_ACCESS_KEY", "pexels": "PEXELS_API_KEY"}


def default_sources() -> list[str]:
    s = [k for k, env in KEYED.items() if os.environ.get(env)]   # keyed, high-quality photo sources first
    return s + ["openverse", "wikimedia"]


def orientation_ok(c, orient):
    if not orient or not c["width"] or not c["height"]:
        return True
    r = c["width"] / c["height"]
    return {"landscape": r >= 1.15, "portrait": r <= 0.9, "square": 0.8 <= r <= 1.25}[orient]


# ------------------------------------------------------------------ fetching
def fetch_to(url_or_path: str, dest: Path, headers=None) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if re.match(r"https?://", url_or_path):
        dest.write_bytes(http(url_or_path, headers, binary=True))
    else:
        shutil.copyfile(Path(url_or_path).expanduser(), dest)
    return dest


def cjk_font(size):
    from PIL import ImageFont
    for p in ("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc", "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc",
              "/System/Library/Fonts/Hiragino Sans GB.ttc", "C:/Windows/Fonts/meiryob.ttc", "C:/Windows/Fonts/YuGothB.ttc", "DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            continue
    return ImageFont.load_default()


def contact_sheet(cands, folder: Path, cols=4) -> Path:
    from PIL import Image, ImageDraw
    tw, th, pad, lab = 420, 280, 18, 58
    rows = (len(cands) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * (tw + pad) + pad, rows * (th + lab + pad) + pad), (22, 22, 26))
    d = ImageDraw.Draw(sheet); f1, f2 = cjk_font(22), cjk_font(16)
    for k, c in enumerate(cands):
        x, y = pad + (k % cols) * (tw + pad), pad + (k // cols) * (th + lab + pad)
        try:
            im = Image.open(folder / c["thumb_file"]).convert("RGB")
            im.thumbnail((tw, th))
            sheet.paste(im, (x + (tw - im.width) // 2, y + (th - im.height) // 2))
        except Exception:
            d.rectangle([x, y, x + tw, y + th], outline=(90, 90, 90)); d.text((x + 10, y + 10), "no preview", fill=(160, 160, 160), font=f2)
        li = lic_info(c["license_code"], c["license_version"])
        flag = "  ⚠attrib" if li["attribution_required"] else ""
        d.text((x, y + th + 6), f"#{k + 1}  {c['width']}×{c['height']}{flag}", fill=(240, 240, 240), font=f1)
        d.text((x, y + th + 32), f"{c['source'][:22]} · {li['license'][:18]}", fill=(170, 170, 180), font=f2)
    path = folder / "sheet.png"
    sheet.save(path)
    return path


# ------------------------------------------------------------------ credits ledger
def load_credits(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def save_credits(path: Path, data: dict):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


def record(path_key: str, cand: dict, credits_path: Path, modified: str = ""):
    li = lic_info(cand["license_code"], cand["license_version"])
    cr = load_credits(credits_path)
    creator = cand.get("creator") or ""
    src = cand["source"]
    if cand["license_code"] == "unsplash":
        attribution = f"Photo by {creator} on Unsplash"
    elif cand["license_code"] == "own":
        attribution = ""
    else:
        attribution = " / ".join(x for x in [f"“{cand.get('title')}”" if cand.get("title") else "", creator, src, li["license"]] if x)
    cr[path_key] = {"title": cand.get("title", ""), "creator": creator, "creator_url": cand.get("creator_url", ""), "source": src,
                    "source_url": cand.get("page", ""), **li, "modified": modified, "attribution": attribution,
                    "retrieved": dt.date.today().isoformat(), "kind": cand.get("kind", "image")}
    save_credits(credits_path, cr)
    return cr[path_key]


# ------------------------------------------------------------------ image processing
def theme_colors(theme: str) -> dict:
    p = Path(theme) if Path(theme).is_file() else THEMES / f"{theme}.css"
    css = p.read_text(encoding="utf-8") if p.exists() else ""
    get = lambda k, d: (re.search(rf"{re.escape(k)}:\s*(#[0-9a-fA-F]{{3,8}})", css) or [None, d])[1]  # noqa: E731
    return {"bg": get("--bg", "#111111"), "fg": get("--fg", "#f5f5f5"), "accent": get("--accent", "#e0452b")}


def hex_rgb(h: str):
    h = h.lstrip("#")
    h = "".join(c * 2 for c in h) if len(h) == 3 else h[:6]
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def lum(rgb):
    f = lambda v: (v / 255) / 12.92 if v / 255 <= .03928 else (((v / 255) + .055) / 1.055) ** 2.4  # noqa: E731
    r, g, b = rgb[:3]
    return .2126 * f(r) + .7152 * f(g) + .0722 * f(b)


def process(src: Path, dest: Path, crop: str | None, focus: str, max_w: int, treat: str, colors: dict, strength: float, zoom: float = 1.0) -> tuple[str, tuple[int, int]]:
    from PIL import Image, ImageOps, ImageFilter
    im = ImageOps.exif_transpose(Image.open(src))
    mods = []
    has_alpha = im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info)
    im = im.convert("RGBA" if has_alpha else "RGB")
    if crop:
        if re.match(r"^\d+x\d+$", crop):
            tw, th = map(int, crop.split("x")); ratio = tw / th
        else:
            a, b = map(float, crop.split(":")); ratio = a / b
        fx, fy = (float(v) for v in focus.split(","))
        w, h = im.size
        cw, ch = (h * ratio, h) if w / h > ratio else (w, w / ratio)   # largest box of that ratio
        cw, ch = int(cw / max(1.0, zoom)), int(ch / max(1.0, zoom))     # --zoom tightens around the focus point
        x0 = int(min(max(0, fx * w - cw / 2), w - cw)); y0 = int(min(max(0, fy * h - ch / 2), h - ch))
        im = im.crop((x0, y0, x0 + cw, y0 + ch)); mods.append(f"cropped {crop}" + (f" (zoom {zoom:g}×)" if zoom > 1 else ""))
    if im.width > max_w:
        im = im.resize((max_w, round(im.height * max_w / im.width)), Image.LANCZOS); mods.append("resized")
    if treat != "none":
        dark = hex_rgb(colors["bg"] if lum(hex_rgb(colors["bg"])) < lum(hex_rgb(colors["fg"])) else colors["fg"])
        rgb = im.convert("RGB")
        if treat == "duotone":
            out = ImageOps.colorize(ImageOps.autocontrast(rgb.convert("L"), cutoff=1), black=dark, white=hex_rgb(colors["accent"]))
        elif treat == "mono":
            out = ImageOps.grayscale(rgb).convert("RGB")
        elif treat == "darken":
            out = Image.blend(rgb, Image.new("RGB", rgb.size, dark), strength)
        elif treat == "tint":
            out = Image.blend(ImageOps.grayscale(rgb).convert("RGB"), Image.new("RGB", rgb.size, hex_rgb(colors["accent"])), strength)
        elif treat == "blur":
            out = rgb.filter(ImageFilter.GaussianBlur(radius=max(4, im.width // 160)))
        else:
            raise SystemExit(f"✗ unknown --treat {treat}")
        im = out; mods.append(f"{treat} colour treatment")
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.suffix.lower() == ".png":
        im.save(dest, optimize=True)
    elif dest.suffix.lower() == ".webp":
        im.convert("RGB").save(dest, quality=84, method=6)
    else:  # JPEG: flatten any transparency onto white
        if im.mode == "RGBA":
            bg = Image.new("RGB", im.size, (255, 255, 255)); bg.paste(im, mask=im.split()[3]); im = bg
        im.convert("RGB").save(dest, quality=84, optimize=True, progressive=True)
    return ", ".join(mods), im.size


# ------------------------------------------------------------------ icons (Iconify: API, then npm @iconify-json)
ICON_LICENSE_FALLBACK = {"tabler": "MIT", "lucide": "ISC", "ph": "MIT", "material-symbols": "Apache-2.0", "mdi": "Apache-2.0",
                         "fluent-emoji-flat": "MIT", "noto": "Apache-2.0", "twemoji": "CC-BY-4.0", "heroicons": "MIT", "carbon": "Apache-2.0"}


def _iconify_pkg(prefix: str) -> dict | None:
    d = CACHE / "iconify" / prefix
    f = d / "package" / "icons.json"
    if not f.exists():
        d.mkdir(parents=True, exist_ok=True)
        try:
            r = subprocess.run(["npm", "pack", f"@iconify-json/{prefix}", "--silent", "--pack-destination", str(d)], capture_output=True, text=True, timeout=180)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return None
        tgz = list(d.glob("*.tgz"))
        if r.returncode or not tgz:
            return None
        with tarfile.open(tgz[0]) as t:
            t.extractall(d)  # noqa: S202 – trusted npm tarball
        tgz[0].unlink()
    data = json.loads(f.read_text(encoding="utf-8"))
    info = d / "package" / "info.json"
    data["_info"] = json.loads(info.read_text(encoding="utf-8")) if info.exists() else {}
    return data


def icon_svg(ref: str) -> tuple[str, dict]:
    """'tabler:rocket' → (svg markup with currentColor, credit dict). Cached on disk."""
    prefix, name = ref.split(":", 1)
    cache = CACHE / "iconify" / "svg" / f"{prefix}__{name}.json"
    if cache.exists():
        d = json.loads(cache.read_text(encoding="utf-8"))
        return d["svg"], d["credit"]
    svg, lic, setname = None, ICON_LICENSE_FALLBACK.get(prefix, "see icon set"), prefix
    try:
        svg = http(f"https://api.iconify.design/{prefix}/{name}.svg", binary=True).decode("utf-8")
    except Exception:
        pkg = _iconify_pkg(prefix)
        if pkg:
            icons, aliases = pkg["icons"], pkg.get("aliases", {})
            key = name if name in icons else aliases.get(name, {}).get("parent")
            if key in icons:
                ic = icons[key]
                w, h = ic.get("width", pkg.get("width", 24)), ic.get("height", pkg.get("height", 24))
                svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="1em" height="1em">{ic["body"]}</svg>'
                lic = pkg["_info"].get("license", {}).get("spdx", lic); setname = pkg["_info"].get("name", prefix)
    if not svg:
        raise LookupError(f"icon not found: {ref} (browse: assets.py icon <word> --sets {prefix} --sheet, or https://icon-sets.iconify.design/)")
    svg = re.sub(r'\s(width|height)="[^"]*"', "", svg, count=2).replace("<svg ", '<svg width="1em" height="1em" ', 1)
    credit = {"title": ref, "creator": setname, "creator_url": "", "source": "Iconify", "source_url": f"https://icon-sets.iconify.design/{prefix}/",
              "license": lic, "license_url": "", "attribution_required": lic.upper().startswith("CC-BY"), "commercial_ok": True,
              "derivatives_ok": True, "share_alike": False, "modified": "", "attribution": f"Icons: {setname} ({lic})", "kind": "icon",
              "retrieved": dt.date.today().isoformat()}
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps({"svg": svg, "credit": credit}), encoding="utf-8")
    return svg, credit


def icon_search(term: str, sets: list[str], limit=24) -> list[str]:
    try:
        d = http("https://api.iconify.design/search?" + urllib.parse.urlencode({"query": term, "limit": 96, "prefixes": ",".join(sets)}))
        return d.get("icons", [])[:limit]
    except Exception:
        pass
    words = term.lower().replace(" ", "-").split("-")
    hits = []
    for p in sets:
        pkg = _iconify_pkg(p)
        if not pkg:
            continue
        names = list(pkg["icons"]) + list(pkg.get("aliases", {}))
        exact = [n for n in names if n == "-".join(words)]
        allw = [n for n in names if all(w in n.split("-") for w in words) and n not in exact]
        part = [n for n in names if any(w in n for w in words) and n not in exact and n not in allw]
        for n in sorted(exact) + sorted(allw, key=len) + sorted(part, key=len)[:8]:
            hits.append(f"{p}:{n}")
    # interleave sets so the sheet shows variety
    by = {}
    for h in hits:
        by.setdefault(h.split(":")[0], []).append(h)
    out = []
    while any(by.values()) and len(out) < limit:
        for k in list(by):
            if by[k]:
                out.append(by[k].pop(0))
    return out[:limit]


def icon_sheet(refs: list[str], path: Path):
    from playwright.sync_api import sync_playwright
    cells = []
    for r in refs:
        try:
            svg, _ = icon_svg(r)
        except LookupError:
            continue
        cells.append(f'<div class="c"><div class="i">{svg}</div><div class="n">{html.escape(r)}</div></div>')
    page_html = ("<html><body style='margin:0;background:#fff;font:14px monospace'><div style='display:grid;grid-template-columns:repeat(6,190px);gap:10px;padding:16px'>"
                 + "".join(cells) + "</div><style>.c{border:1px solid #ddd;border-radius:10px;padding:14px;text-align:center}.i{font-size:64px;color:#1a1a1a;height:72px}.n{margin-top:6px;word-break:break-all;color:#555}</style></body></html>")
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1220, "height": 400}); pg.set_content(page_html)
        pg.screenshot(path=str(path), full_page=True); b.close()


# ------------------------------------------------------------------ commands
def cmd_search(a):
    sources = [s.strip() for s in (a.sources.split(",") if a.sources else default_sources()) if s.strip()]
    out_dir = Path(a.out or f"img/_cand/{slugify(a.query)}")
    out_dir.mkdir(parents=True, exist_ok=True)
    cands, notes = [], []
    for s in sources:
        try:
            if s.startswith("local:"):
                got = src_local(a.query, a.kind, a.orientation, a.n, Path(s[6:]))
            else:
                got = SOURCES[s](a.query, a.kind, a.orientation, a.n)
            notes.append(f"{s}: {len(got)}")
            cands += got
        except KeyError:
            notes.append(f"{s}: unknown source")
        except Exception as e:  # network blocked, rate limit, missing key …
            notes.append(f"{s}: skipped ({type(e).__name__}: {str(e)[:80]})")
    kept, dropped = [], {"nc": 0, "nd": 0, "small": 0, "orient": 0, "unknown": 0}
    for c in cands:
        li = lic_info(c["license_code"], c["license_version"])
        if c["license_code"] not in LICENSES:
            dropped["unknown"] += 1; continue
        if not li["commercial_ok"] and not a.allow_nc:
            dropped["nc"] += 1; continue
        if not li["derivatives_ok"] and not a.allow_nd:
            dropped["nd"] += 1; continue
        if c["width"] and c["width"] < a.min_width:
            dropped["small"] += 1; continue
        if not orientation_ok(c, a.orientation):
            dropped["orient"] += 1; continue
        kept.append(c)
    kept = kept[: a.max]

    def thumb(ic):
        k, c = ic
        ext = os.path.splitext(urllib.parse.urlparse(c["thumb"]).path)[1].lower()
        name = f"{k + 1:02d}{ext if ext in IMG_EXT else '.jpg'}"
        try:
            fetch_to(c["thumb"], out_dir / name); c["thumb_file"] = name
        except Exception:
            c["thumb_file"] = ""
        return c
    with cf.ThreadPoolExecutor(8) as ex:
        kept = list(ex.map(thumb, enumerate(kept)))
    (out_dir / "candidates.json").write_text(json.dumps({"query": a.query, "kind": a.kind, "candidates": kept}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"sources → {'; '.join(notes)}")
    drops = ", ".join(f"{v} {k}" for k, v in dropped.items() if v)
    print(f"{'✓' if kept else '✗'} {len(kept)} candidates for “{a.query}”" + (f"  (filtered out: {drops})" if drops else ""))
    if kept:
        sheet = contact_sheet(kept, out_dir)
        print(f"  contact sheet: {sheet}   ← LOOK at it, then: assets.py pick {out_dir} <#> --as img/<name>.jpg --crop 16:9")
        for k, c in enumerate(kept, 1):
            li = lic_info(c["license_code"], c["license_version"])
            print(f"  #{k:<2} {c['width']}×{c['height']:<5} {li['license']:<22} {c['source'][:24]:<24} {strip_html(c['title'])[:48]}")
    else:
        print("  nothing usable — try an English query with concrete nouns, another --kind, or an icon/diagram instead of a photo")
    return 0 if kept else 1


def cmd_pick(a):
    folder = Path(a.cand_dir)
    data = json.loads((folder / "candidates.json").read_text(encoding="utf-8"))
    c = data["candidates"][a.num - 1]
    c["kind"] = data.get("kind", "photo")
    li = lic_info(c["license_code"], c["license_version"])
    if (a.crop or a.treat != "none") and not li["derivatives_ok"]:
        sys.exit(f"✗ {li['license']} forbids modifications – use it uncropped/untreated (drop --crop/--treat) or pick another")
    dest = Path(a.as_)
    raw = CACHE / "originals" / (hashlib.md5(c["full"].encode()).hexdigest() + (os.path.splitext(urllib.parse.urlparse(c["full"]).path)[1] or ".jpg"))
    if not raw.exists():
        fetch_to(c["full"], raw)
    if c["license_code"] == "unsplash" and c["extra"].get("download_location") and os.environ.get("UNSPLASH_ACCESS_KEY"):
        try:  # required by the Unsplash API guidelines whenever a photo is used
            http(c["extra"]["download_location"], {"Authorization": f"Client-ID {os.environ['UNSPLASH_ACCESS_KEY']}"})
        except Exception:
            pass
    colors = theme_colors(a.theme) if a.theme else {"bg": "#111111", "fg": "#f5f5f5", "accent": "#e0452b"}
    if a.colors:
        d, l = a.colors.split(",")
        colors = {"bg": d.strip(), "fg": "#ffffff", "accent": l.strip()}
    mods, size = process(raw, dest, a.crop, a.focus, a.max, a.treat, colors, a.strength, a.zoom)
    key = os.path.relpath(dest, Path(a.credits).parent).replace(os.sep, "/")
    rec = record(key, c, Path(a.credits), mods)
    print(f"✓ {dest}  {size[0]}×{size[1]}  [{rec['license']}]" + (f"  modified: {mods}" if mods else ""))
    if rec["attribution_required"]:
        print(f"  attribution required → build.py will add: {rec['attribution']}")
    if rec["share_alike"]:
        print("  ⚠ share-alike: modified versions must stay under the same licence (fine for a talk; note it if you redistribute the deck)")
    if size[0] < 1600 and a.crop and a.crop.startswith("16:9"):
        print(f"  ⚠ only {size[0]}px wide – will look soft full-bleed on a 1920px stage; use it in a smaller frame")


def cmd_icon(a):
    sets = [s.strip() for s in a.sets.split(",")]
    cr_path = Path(a.credits)
    for term in a.terms:
        if ":" in term:
            refs = [term]
        else:
            refs = icon_search(term, sets, limit=a.n)
        if not refs:
            print(f"✗ no icon for “{term}” in {', '.join(sets)} – try a synonym (English) or another set"); continue
        print(f"“{term}”: " + "  ".join(refs[: a.n]))
        if a.sheet:
            p = Path(a.dir) / f"_sheet-{slugify(term)}.png"; p.parent.mkdir(parents=True, exist_ok=True)
            icon_sheet(refs[: a.n], p); print(f"  sheet: {p}  ← look, then use <i class=\"ico\" data-icon=\"<set:name>\"></i>")
        if a.save:
            svg, credit = icon_svg(refs[0])
            f = Path(a.dir) / f"{refs[0].replace(':', '__')}.svg"; f.parent.mkdir(parents=True, exist_ok=True); f.write_text(svg, encoding="utf-8")
            cr = load_credits(cr_path); cr[f"iconset:{refs[0].split(':')[0]}"] = credit; save_credits(cr_path, cr)
            print(f"  saved {f}")


def cmd_add(a):
    p = Path(a.path)
    if not p.exists():
        sys.exit(f"✗ {p} not found")
    code, ver = ("own", "") if a.own else parse_license_text(a.license or "")
    if not a.own and code not in LICENSES:
        sys.exit(f"✗ licence “{a.license}” not recognised. Use --own, or e.g. 'CC BY 4.0', 'CC0', 'Pixabay', 'Unsplash', 'Pexels'")
    cand = {"source": a.source or ("Own" if a.own else "Web"), "title": a.title or "", "creator": a.creator or "", "creator_url": a.creator_url or "",
            "page": a.source_url or "", "license_code": code, "license_version": ver, "kind": "image"}
    key = os.path.relpath(p, Path(a.credits).parent).replace(os.sep, "/")
    rec = record(key, cand, Path(a.credits))
    print(f"✓ recorded {key} [{rec['license']}]")


def cmd_fetch(a):
    if not a.license:
        sys.exit("✗ --license is required: only use web images whose licence you have verified on the source page")
    code, ver = parse_license_text(a.license)
    li = lic_info(code, ver)
    if code not in LICENSES:
        sys.exit(f"✗ licence “{a.license}” not recognised")
    if not li["commercial_ok"] and not a.allow_nc:
        sys.exit(f"✗ {li['license']} is non-commercial – pass --allow-nc only for personal/non-commercial use")
    raw = CACHE / "originals" / hashlib.md5(a.url.encode()).hexdigest()
    fetch_to(a.url, raw)
    dest = Path(a.as_)
    if (a.crop or a.treat != "none") and not li["derivatives_ok"]:
        sys.exit(f"✗ {li['license']} forbids modifications")
    colors = theme_colors(a.theme) if a.theme else {"bg": "#111111", "fg": "#f5f5f5", "accent": "#e0452b"}
    mods, size = process(raw, dest, a.crop, a.focus, a.max, a.treat, colors, a.strength, a.zoom)
    cand = {"source": a.source or urllib.parse.urlparse(a.source_url or a.url).netloc, "title": a.title or "", "creator": a.creator or "",
            "creator_url": "", "page": a.source_url or a.url, "license_code": code, "license_version": ver, "kind": "image"}
    key = os.path.relpath(dest, Path(a.credits).parent).replace(os.sep, "/")
    rec = record(key, cand, Path(a.credits), mods)
    print(f"✓ {dest} {size[0]}×{size[1]} [{rec['license']}]")


def used_images(src_html: str) -> list[str]:
    refs = re.findall(r'(?:src|poster)=["\']([^"\']+)["\']', src_html) + re.findall(r"url\(['\"]?([^)'\"]+)['\"]?\)", src_html)
    return [r for r in dict.fromkeys(refs) if not re.match(r"(data:|https?:|//)", r) and os.path.splitext(r)[1].lower() in IMG_EXT]


def cmd_credits(a):
    cr = load_credits(Path(a.credits))
    deck = Path(a.deck) if a.deck else None
    used = used_images(deck.read_text(encoding="utf-8")) if deck and deck.exists() else [k for k in cr if not k.startswith("iconset:")]
    missing = [u for u in used if u not in cr]
    for u in used:
        r = cr.get(u)
        print(f"  {'✓' if r else '✗'} {u:<34} {r['license'] if r else 'NO LICENCE RECORD'}" + (f"  – {r['attribution']}" if r and r.get("attribution") else ""))
    for k, r in cr.items():
        if k.startswith("iconset:"):
            print(f"  ✓ {k:<34} {r['license']}")
    if missing:
        print(f"✗ {len(missing)} image(s) without a licence record → assets.py add <path> --own | --license … --creator … --source-url …")
    return 1 if missing else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--credits", default="credits.json", help="licence ledger (default ./credits.json, next to deck.src.html)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("search", help="find candidates + contact sheet")
    s.add_argument("query")
    s.add_argument("--kind", default="photo", choices=["photo", "illustration", "vector", "any"])
    s.add_argument("--orientation", choices=["landscape", "portrait", "square"])
    s.add_argument("--sources", help="comma list: nasa,openverse,wikimedia,pixabay,unsplash,pexels,local:DIR (nasa is opt-in: use it for space topics)")
    s.add_argument("--n", type=int, default=PER_SOURCE, help="per source")
    s.add_argument("--max", type=int, default=16, help="max candidates on the sheet")
    s.add_argument("--min-width", type=int, default=MIN_WIDTH)
    s.add_argument("--allow-nc", action="store_true"); s.add_argument("--allow-nd", action="store_true")
    s.add_argument("--out")

    def proc_args(p):
        p.add_argument("--as", dest="as_", required=True, help="output path, e.g. img/hero.jpg")
        p.add_argument("--crop", help="aspect '16:9' '4:3' '1:1' '3:4' or exact '1200x800'")
        p.add_argument("--focus", default="0.5,0.5", help="crop centre as x,y fractions (0.5,0.35 keeps faces/skies)")
        p.add_argument("--zoom", type=float, default=1.0, help="with --crop: tighten the crop around --focus (2 = half the width)")
        p.add_argument("--max", type=int, default=2400, help="max width px (2400 covers full-bleed 1920 with headroom)")
        p.add_argument("--treat", default="none", choices=["none", "duotone", "mono", "darken", "tint", "blur"])
        p.add_argument("--strength", type=float, default=0.45, help="darken/tint amount 0-1")
        p.add_argument("--theme", help="theme name/path for treatment colours")
        p.add_argument("--colors", help="duotone 'dark,light' hex override")

    pk = sub.add_parser("pick", help="download + process + record a candidate")
    pk.add_argument("cand_dir"); pk.add_argument("num", type=int); proc_args(pk)

    ic = sub.add_parser("icon", help="search/browse/save icons")
    ic.add_argument("terms", nargs="+"); ic.add_argument("--sets", default=",".join(DEFAULT_ICON_SETS))
    ic.add_argument("--n", type=int, default=12); ic.add_argument("--sheet", action="store_true")
    ic.add_argument("--save", action="store_true", help="save the best match as an .svg file too")
    ic.add_argument("--dir", default="img/icons")

    ad = sub.add_parser("add", help="record an image you already have")
    ad.add_argument("path"); ad.add_argument("--own", action="store_true"); ad.add_argument("--license")
    for f in ("title", "creator", "creator-url", "source", "source-url"):
        ad.add_argument(f"--{f}")

    fe = sub.add_parser("fetch", help="download a specific web image whose licence you verified")
    fe.add_argument("url"); proc_args(fe); fe.add_argument("--license"); fe.add_argument("--allow-nc", action="store_true")
    for f in ("title", "creator", "source", "source-url"):
        fe.add_argument(f"--{f}")

    c = sub.add_parser("credits", help="licence report"); c.add_argument("deck", nargs="?")
    a = ap.parse_args()
    try:
        from PIL import Image  # noqa: F401
    except ImportError:
        sys.exit("✗ Pillow missing: pip install pillow")
    rc = {"search": cmd_search, "pick": cmd_pick, "icon": cmd_icon, "add": cmd_add, "fetch": cmd_fetch, "credits": cmd_credits}[a.cmd](a)
    sys.exit(rc or 0)


if __name__ == "__main__":
    main()
