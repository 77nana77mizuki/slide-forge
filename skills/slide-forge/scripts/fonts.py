#!/usr/bin/env python3
"""Font handling for Slide Forge.

Theme files declare fonts in their header comment:
    @font Zen Kaku Gothic New | 400,700,900      (static weights)
    @font Murecho | 400..900                     (variable axis range)

Two delivery modes:
  link   – <link> to Google Fonts (default; smallest file, needs internet when presenting)
  embed  – base64 @font-face for ONLY the unicode-range subsets the deck actually uses.
           Works offline (conference Wi-Fi!). Sources tried in order:
             1. Google Fonts CSS API (woff2 subsets)
             2. npm @fontsource / @fontsource-variable packages (via `npm pack`)
"""
from __future__ import annotations

import base64
import json
import os
import re
import subprocess
import tarfile
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

CACHE = Path(os.environ.get("SLIDE_FORGE_CACHE", Path.home() / ".cache" / "slide-forge"))
# Google returns woff2 + unicode-range subsets only for modern browser user agents
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0 Safari/537.36"
HTTP_TIMEOUT = 20  # seconds; Google Fonts normally answers in <1s


@dataclass
class FontSpec:
    family: str
    weights: list[str]      # ["400","700"]  or ["400..900"] for variable

    @property
    def is_range(self) -> bool:
        return any(".." in w for w in self.weights)

    def google_param(self) -> str:
        fam = self.family.replace(" ", "+")
        return f"{fam}:wght@{';'.join(self.weights)}"

    @property
    def slug(self) -> str:
        return re.sub(r"[^a-z0-9]+", "-", self.family.lower()).strip("-")


def parse_theme_fonts(css: str) -> list[FontSpec]:
    specs = []
    for m in re.finditer(r"@font\s+([^|\n]+)\|\s*([^\n*]+)", css):
        fam = m.group(1).strip()
        weights = [w.strip() for w in m.group(2).split(",") if w.strip()]
        specs.append(FontSpec(fam, weights))
    return specs


def google_css_url(specs: list[FontSpec]) -> str:
    return "https://fonts.googleapis.com/css2?" + "&".join(f"family={s.google_param()}" for s in specs) + "&display=swap"


def link_tags(specs: list[FontSpec]) -> str:
    if not specs:
        return ""
    return ('<link rel="preconnect" href="https://fonts.googleapis.com">\n'
            '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
            f'<link rel="stylesheet" href="{google_css_url(specs)}">')


# ---------------------------------------------------------------- unicode-range subsetting
def parse_ranges(ur: str) -> list[tuple[int, int]]:
    out = []
    for part in ur.split(","):
        part = part.strip().upper().replace("U+", "")
        if not part:
            continue
        if "?" in part:  # wildcard form U+4??
            lo, hi = int(part.replace("?", "0"), 16), int(part.replace("?", "F"), 16)
        elif "-" in part:
            a, b = part.split("-")
            lo, hi = int(a, 16), int(b, 16)
        else:
            lo = hi = int(part, 16)
        out.append((lo, hi))
    return out


def block_needed(block: str, used: set[int]) -> bool:
    m = re.search(r"unicode-range:\s*([^;]+);", block)
    if not m:
        return True
    for lo, hi in parse_ranges(m.group(1)):
        if any(lo <= cp <= hi for cp in used):
            return True
    return False


def used_codepoints(text: str) -> set[int]:
    base = set(range(0x20, 0x7F))                          # ASCII always (numbers, page chrome)
    base |= {ord(c) for c in "・、。「」『』（）！？：／ー―…〜％＋－×→←↑↓●○■□◆◇★☆"}
    return base | {ord(c) for c in text if ord(c) >= 0x20}


# ---------------------------------------------------------------- sources
def _http(url: str, binary=False):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as r:
        data = r.read()
    return data if binary else data.decode("utf-8")


def _cached(url: str) -> bytes:
    CACHE.mkdir(parents=True, exist_ok=True)
    key = CACHE / ("g_" + re.sub(r"[^\w.-]", "_", url)[-180:])
    if key.exists():
        return key.read_bytes()
    data = _http(url, binary=True)
    key.write_bytes(data)
    return data


def from_google(specs: list[FontSpec], used: set[int]) -> tuple[str, int]:
    css = _http(google_css_url(specs))
    blocks = re.findall(r"@font-face\s*{[^}]+}", css)
    out, n = [], 0
    for b in blocks:
        if not block_needed(b, used):
            continue
        url = re.search(r"url\((https://[^)]+)\)", b).group(1)
        data = base64.b64encode(_cached(url)).decode()
        b = re.sub(r"src:[^;]+;", f"src: url(data:font/woff2;base64,{data}) format('woff2');", b)
        out.append(b); n += 1
    return "\n".join(out), n


def _npm_pkg(name: str) -> Path | None:
    """Download an npm package tarball into the cache (no node_modules needed)."""
    dest = CACHE / "npm" / name.replace("/", "__")
    if (dest / "package").exists():
        return dest / "package"
    dest.mkdir(parents=True, exist_ok=True)
    try:
        res = subprocess.run(["npm", "pack", name, "--silent", "--pack-destination", str(dest)],
                             capture_output=True, text=True, timeout=180)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    tgz = [p for p in dest.glob("*.tgz")]
    if res.returncode != 0 or not tgz:
        return None
    with tarfile.open(tgz[0]) as t:
        t.extractall(dest)  # noqa: S202 – trusted npm tarball
    tgz[0].unlink()
    return dest / "package"


def from_fontsource(specs: list[FontSpec], used: set[int]) -> tuple[str, int, list[str]]:
    out, n, missing = [], 0, []
    for s in specs:
        if s.is_range:
            pkg = _npm_pkg(f"@fontsource-variable/{s.slug}") or _npm_pkg(f"@fontsource/{s.slug}")
            files = ["wght.css", "index.css"] if pkg and "variable" in str(pkg) else [f"{w}.css" for w in ("400", "700", "900")]
        else:
            pkg = _npm_pkg(f"@fontsource/{s.slug}")
            files = [f"{w}.css" for w in s.weights]
        if not pkg:
            missing.append(s.family); continue
        for fname in files:
            f = pkg / fname
            if not f.exists():
                continue
            css = f.read_text()
            for b in re.findall(r"@font-face\s*{[^}]+}", css):
                if not block_needed(b, used):
                    continue
                m = re.search(r"url\(\./(files/[^)]+\.woff2)\)", b)
                if not m:
                    continue
                data = base64.b64encode((pkg / m.group(1)).read_bytes()).decode()
                b = re.sub(r"font-family:\s*'([^']+?)(?: Variable)?';", f"font-family: '{s.family}';", b)
                b = re.sub(r"src:[^;]+;", f"src: url(data:font/woff2;base64,{data}) format('woff2');", b)
                out.append(b); n += 1
            if s.is_range:
                break
    return "\n".join(out), n, missing


def embed_css(specs: list[FontSpec], text: str, log=print) -> str:
    used = used_codepoints(text)
    try:
        css, n = from_google(specs, used)
        log(f"  fonts: embedded {n} subset files from Google Fonts")
        return css
    except Exception as e:  # network blocked, offline, etc.
        log(f"  fonts: Google Fonts unavailable ({type(e).__name__}); trying npm @fontsource …")
    css, n, missing = from_fontsource(specs, used)
    log(f"  fonts: embedded {n} subset files from @fontsource" + (f"; NOT FOUND: {', '.join(missing)} (system fallback will be used)" if missing else ""))
    return css


if __name__ == "__main__":
    import sys
    css = Path(sys.argv[1]).read_text()
    specs = parse_theme_fonts(css)
    print(json.dumps([s.__dict__ for s in specs], ensure_ascii=False, indent=1))
    print(google_css_url(specs))
