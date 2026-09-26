// Headless renderer driven by scripts/video.py (one bundle + one browser for all work).
//   node render.mjs video  --out out/movie.mp4 [--crf 18] [--scale 1] [--concurrency N] [--codec h264]
//   node render.mjs stills --frames 12,90,200 --outdir out/stills [--scale 0.5]
//   node render.mjs det    --frame 120 --outdir out/det            (renders the frame twice, in fresh tabs)
// Env: SF_BROWSER (chrome/headless_shell path, optional), SF_GL (default swangle).
import { bundle } from "@remotion/bundler";
import { openBrowser, renderMedia, renderStill, selectComposition } from "@remotion/renderer";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const [mode, ...rest] = process.argv.slice(2);
const arg = (k, d) => { const i = rest.indexOf(`--${k}`); return i >= 0 ? rest[i + 1] : d; };
const root = path.dirname(new URL(import.meta.url).pathname);
const gl = process.env.SF_GL || "swangle";
const browserExecutable = process.env.SF_BROWSER || null;
const chromiumOptions = { gl };
const logLevel = process.env.SF_LOG || "error";

const t0 = Date.now();
const serveUrl = await bundle({ entryPoint: path.join(root, "src/index.ts"), publicDir: path.join(root, "public") });
const browser = await openBrowser("chrome", { browserExecutable, chromiumOptions, logLevel });
const comp = await selectComposition({ serveUrl, id: "Movie", puppeteerInstance: browser, browserExecutable, chromiumOptions, logLevel });
const scale = parseFloat(arg("scale", "1"));
const log = (m) => console.log(`[render] ${m}`);
log(`composition ${comp.width}x${comp.height} @${comp.fps}fps, ${comp.durationInFrames} frames (${(comp.durationInFrames / comp.fps).toFixed(1)}s)`);

try {
  if (mode === "video") {
    const out = path.resolve(arg("out", "out/movie.mp4"));
    fs.mkdirSync(path.dirname(out), { recursive: true });
    const concurrency = parseInt(arg("concurrency", String(Math.max(1, Math.min(8, os.cpus().length)))), 10);
    let last = -1;
    await renderMedia({
      composition: comp, serveUrl, codec: arg("codec", "h264"), outputLocation: out, crf: parseInt(arg("crf", "18"), 10),
      scale, concurrency, puppeteerInstance: browser, browserExecutable, chromiumOptions, logLevel, timeoutInMilliseconds: 120000,
      onProgress: ({ progress }) => { const p = Math.floor(progress * 10); if (p !== last) { last = p; log(`${p * 10}%`); } },
    });
    log(`wrote ${out}`);
  } else if (mode === "stills" || mode === "det") {
    const outdir = path.resolve(arg("outdir", "out/stills"));
    fs.mkdirSync(outdir, { recursive: true });
    const frames = mode === "det" ? [parseInt(arg("frame", "0"), 10), parseInt(arg("frame", "0"), 10)] : arg("frames", "0").split(",").map(Number);
    for (const [i, frame] of frames.entries()) {
      const f = Math.max(0, Math.min(comp.durationInFrames - 1, frame));
      const name = mode === "det" ? `det-${i + 1}.png` : `f${String(f).padStart(5, "0")}.png`;
      await renderStill({ composition: comp, serveUrl, frame: f, output: path.join(outdir, name), scale, imageFormat: "png",
        puppeteerInstance: browser, browserExecutable, chromiumOptions, logLevel, timeoutInMilliseconds: 120000 });
      log(`still ${f} → ${name}`);
    }
  } else {
    throw new Error(`unknown mode ${mode}`);
  }
} finally {
  await browser.close({ silent: true });
}
log(`done in ${((Date.now() - t0) / 1000).toFixed(1)}s`);
