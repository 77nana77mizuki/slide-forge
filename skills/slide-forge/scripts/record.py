#!/usr/bin/env python3
"""Record the deck (with real animations and transitions) to a video — for sharing on
Slack/SNS, async review, or checking motion as the audience will see it.

    python scripts/record.py deck.html                      # → deck.webm (+ deck.mp4 if ffmpeg exists)
    python scripts/record.py deck.html --dwell 2500 --step-dwell 1200 --size 1280x720

Each slide is shown for --dwell ms after entering, each build step for --step-dwell ms.
Per-slide override: <section data-dwell="4000">.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sys.exit("✗ Playwright missing:  pip install playwright && python -m playwright install chromium")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("deck", type=Path)
    ap.add_argument("-o", "--out", type=Path)
    ap.add_argument("--dwell", type=int, default=2600, help="ms on each slide after it enters")
    ap.add_argument("--step-dwell", type=int, default=1300, help="ms after each build step")
    ap.add_argument("--size", default="1920x1080")
    a = ap.parse_args()
    w, h = map(int, a.size.lower().split("x"))
    out = a.out or a.deck.with_suffix(".webm")
    tmp = Path(tempfile.mkdtemp(prefix="sf-rec-"))

    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(viewport={"width": w, "height": h}, record_video_dir=str(tmp), record_video_size={"width": w, "height": h})
        page = ctx.new_page()
        page.add_init_script("try{sessionStorage.setItem('sf-hint','1')}catch(e){}")   # no help toast in the video
        page.goto(a.deck.resolve().as_uri() + "#/1", wait_until="load")
        page.wait_for_function("document.documentElement.classList.contains('sf-ready')", timeout=30000)
        n = page.evaluate("() => deck.count")
        for i in range(n):
            if i:
                page.evaluate(f"() => deck.go({i}, 0, {{dir: 1}})")
            dwell = page.evaluate(f"() => +deck.slides()[{i}].dataset.dwell || 0") or a.dwell
            page.wait_for_timeout(dwell)
            for _ in range(page.evaluate("() => deck.steps()")):
                page.evaluate("() => deck.next()")
                page.wait_for_timeout(a.step_dwell)
        page.wait_for_timeout(600)
        video = page.video.path()
        ctx.close(); b.close()
    shutil.move(video, out)
    print(f"✓ video {out}  ({out.stat().st_size / 1024 / 1024:.1f} MB)")
    if shutil.which("ffmpeg"):
        mp4 = out.with_suffix(".mp4")
        r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(out), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", str(mp4)])
        if r.returncode == 0:
            print(f"✓ mp4   {mp4}")


if __name__ == "__main__":
    main()
