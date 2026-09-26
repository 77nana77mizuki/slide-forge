/* Kinetic typography, Japanese-aware.
   - Splits text into BudouX phrases (the same units the browser uses for word-break: auto-phrase), so
     phrase-by-phrase motion never breaks a word and lines still wrap at natural points.
   - Inline marks:  **accent**  ==highlight==  __underline__  ((circle))   ·  "\n" forces a line break.
   - Effects: rise · pop · blur · mask · slam · type · tracking · scramble · shimmer  (every value derived from the frame).
     scramble = decrypt reveal (seeded glyphs), shimmer = rise + a light sweep across the settled line. */
import React from "react";
import { useCurrentFrame } from "remotion";
import { loadDefaultJapaneseParser } from "budoux";
import { Circle as RCircle, Highlight, Underline } from "@remotion/rough-notation";
import { EASE, prog, pscale, useMotion } from "./motion";
import { mulberry32 } from "./lib";

const GLYPHS_JA = "アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲン";
const GLYPHS_LAT = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789#%&*+=<>";
/** deterministic stand-in glyph for char `c` at frame `f` (changes every 2 frames) */
const scrambleGlyph = (c: string, i: number, f: number) => {
  if (/\s/.test(c)) return c;
  const r = mulberry32(i * 7919 + Math.floor(f / 2) * 104729)();
  const set = c.charCodeAt(0) > 0x2e80 ? GLYPHS_JA : GLYPHS_LAT;
  return set[Math.floor(r * set.length)];
};

export type Effect = "rise" | "pop" | "blur" | "mask" | "slam" | "type" | "tracking" | "scramble" | "shimmer";
export type By = "char" | "phrase" | "line";
type Mark = null | "accent" | "highlight" | "underline" | "circle";
type Seg = { text: string; mark: Mark };

const parser = loadDefaultJapaneseParser();
const MARK_RE = /\*\*(.+?)\*\*|==(.+?)==|__(.+?)__|\(\((.+?)\)\)/g;

export const parseMarks = (line: string): Seg[] => {
  const out: Seg[] = []; let last = 0; let m: RegExpExecArray | null;
  MARK_RE.lastIndex = 0;
  while ((m = MARK_RE.exec(line))) {
    if (m.index > last) out.push({ text: line.slice(last, m.index), mark: null });
    const mark: Mark = m[1] !== undefined ? "accent" : m[2] !== undefined ? "highlight" : m[3] !== undefined ? "underline" : "circle";
    out.push({ text: m[1] ?? m[2] ?? m[3] ?? m[4], mark });
    last = m.index + m[0].length;
  }
  if (last < line.length) out.push({ text: line.slice(last), mark: null });
  return out;
};
export const stripMarks = (s: string) => s.replace(MARK_RE, (_a, a, b, c, d) => a ?? b ?? c ?? d);

/** phrases of one segment: BudouX for Japanese, whitespace-delimited words for Latin (spaces kept) */
const phrases = (s: string): string[] => {
  if (!s) return [];
  const out: string[] = [];
  for (const chunk of s.split(/(?<=\s)/)) out.push(...(/[　-鿿＀-￯]/.test(chunk) ? parser.parse(chunk) : [chunk]));
  return out.filter((p) => p.length);
};

type Unit = { text: string; mark: Mark; group: number; line: number };
/** Units in reading order. Marked segments stay one group so their annotation wraps the whole span. */
export const layoutUnits = (text: string, by: By): Unit[][] => {
  let group = 0;
  return text.split("\n").map((line, li) => {
    const units: Unit[] = [];
    if (by === "line") { units.push({ text: line, mark: null, group: group++, line: li }); return units; }
    for (const seg of parseMarks(line)) {
      const ph = seg.mark ? [seg.text] : phrases(seg.text);
      for (const p of ph) {
        const g = group++;
        if (by === "char") for (const ch of Array.from(p)) units.push({ text: ch, mark: seg.mark, group: g, line: li });
        else units.push({ text: p, mark: seg.mark, group: g, line: li });
      }
    }
    return units;
  });
};

/** Frames from `start` until the last unit has settled. */
export const buildFrames = (text: string, by: By, m: ReturnType<typeof useMotion>, effect: Effect) => {
  const lines = layoutUnits(text, by);
  const n = lines.reduce((a, l) => a + l.length, 0);
  const st = effect === "tracking" ? 0 : by === "char" ? m.staggerChar : by === "phrase" ? m.staggerWord : m.staggerLine;
  return Math.max(0, n - 1) * st + (lines.length - 1) * (by === "line" ? 0 : m.staggerLine * 0.5) + m.dur;
};

export type KProps = {
  text: string; start?: number; effect?: Effect; by?: By; out?: number;   // `out`: frame where the exit starts
  style?: React.CSSProperties; accent: string; markColor?: string; lineGap?: number; align?: "left" | "center";
};

export const KText: React.FC<KProps> = ({ text, start = 0, effect = "rise", by, out, style, accent, markColor, lineGap = 0, align = "left" }) => {
  const f = useCurrentFrame();
  const m = useMotion();
  const unitBy: By = by ?? (effect === "type" || effect === "scramble" ? "char" : effect === "tracking" ? "line" : "phrase");
  const lines = layoutUnits(text, unitBy);
  const st = effect === "tracking" ? 0 : unitBy === "char" ? m.staggerChar : unitBy === "phrase" ? m.staggerWord : m.staggerLine;
  const total = lines.reduce((a, l) => a + l.length, 0);
  let idx = 0;
  const lineStart: number[] = [];
  const rows = lines.map((units, li) => {
    lineStart[li] = start + idx * st + li * (unitBy === "line" ? 0 : m.staggerLine * 0.5);
    const spans = units.map((u) => {
      const i = idx++;
      const s0 = start + i * st + li * (unitBy === "line" ? 0 : m.staggerLine * 0.5);
      const p = prog(f, s0, m.dur, m.enter);
      // exit: reverse order, quicker, accelerating
      const q = out !== undefined ? prog(f, out + (total - 1 - i) * st * 0.5, m.dur * 0.7, EASE.exit) : 0;
      let st2: React.CSSProperties = { display: "inline-block", whiteSpace: "pre" };
      switch (effect) {
        case "pop": st2 = { ...st2, opacity: Math.min(1, p * 2.5), scale: String(pscale(f, s0, m.dur * 1.6, 0.35, 1, m.pop)) }; break;
        case "blur": st2 = { ...st2, opacity: p, filter: `blur(${(1 - p) * 18}px)`, translate: `0 ${(1 - p) * m.distance * 0.35}px` }; break;
        case "slam": st2 = { ...st2, opacity: Math.min(1, p * 3), scale: String(pscale(f, s0, m.dur, 2.2, 1, EASE.snap)) }; break;
        case "type": st2 = { ...st2, opacity: f >= s0 ? 1 : 0 }; break;
        case "scramble": st2 = { ...st2, opacity: f >= s0 - m.dur ? 1 : 0, color: p < 1 ? accent : undefined }; break;
        case "tracking": st2 = { ...st2, opacity: p }; break;
        case "mask": st2 = { ...st2, translate: `0 ${(1 - p) * 110}%` }; break;
        default: st2 = { ...st2, opacity: p, translate: `0 ${(1 - p) * m.distance}px` };
      }
      if (q > 0) st2 = { ...st2, opacity: (Number(st2.opacity ?? 1)) * (1 - q), translate: `0 ${-q * m.distance * 0.5}px` };
      if (u.mark === "accent") st2.color = accent;
      const shown = effect === "scramble" && p < 1 ? Array.from(u.text).map((c, k) => scrambleGlyph(c, i * 31 + k, f)).join("") : u.text;
      const inner = <span style={st2}>{shown}</span>;
      const node = effect === "mask" ? <span style={{ display: "inline-block", overflow: "hidden", verticalAlign: "bottom", paddingBottom: "0.08em" }}>{inner}</span> : inner;
      return { u, node, s0 };
    });
    // group consecutive units of the same phrase/mark so marks wrap whole spans and phrases never split
    const groups: { u: Unit; nodes: React.ReactNode[]; s0: number; s1: number }[] = [];
    for (const s of spans) {
      const g = groups[groups.length - 1];
      if (g && g.u.group === s.u.group) { g.nodes.push(s.node); g.s1 = s.s0; } else groups.push({ u: s.u, nodes: [s.node], s0: s.s0, s1: s.s0 });
    }
    return (
      <div key={li} style={{ display: "block", textAlign: align, marginTop: li ? lineGap : 0 }}>
        {groups.map((g, gi) => {
          const content = <span key={gi} style={{ display: "inline-block", whiteSpace: "nowrap" }}>{g.nodes.map((n, k) => <React.Fragment key={k}>{n}</React.Fragment>)}</span>;
          if (!g.u.mark || g.u.mark === "accent") return content;
          const mp = prog(f, g.s1 + m.dur * 0.6, 18 * (m.fps / 30), EASE.standard);
          const c = markColor ?? accent;
          if (g.u.mark === "highlight") return <Highlight key={gi} color={c} progress={mp}>{content}</Highlight>;
          if (g.u.mark === "underline") return <Underline key={gi} color={c} strokeWidth={6} progress={mp}>{content}</Underline>;
          return <RCircle key={gi} color={c} strokeWidth={5} padding={{ top: 10, bottom: 10, left: 16, right: 16 }} progress={mp}>{content}</RCircle>;
        })}
      </div>
    );
  });
  const caret = effect === "type" && f < start + total * st + m.fps * 1.2 && Math.floor(f / (m.fps / 2)) % 2 === 0;
  const trackP = effect === "tracking" ? prog(f, start, m.dur * 2.2, EASE.standard) : 1;
  const settle = start + Math.max(0, total - 1) * st + m.dur;
  const sweep = effect === "shimmer" ? prog(f, settle, m.fps * 1.1, EASE.standard) : 0;
  const shimmerStyle: React.CSSProperties = effect === "shimmer" && sweep > 0 && sweep < 1 ? {
    backgroundImage: `linear-gradient(100deg, currentColor 0%, currentColor ${sweep * 130 - 30}%, #fff ${sweep * 130 - 15}%, currentColor ${sweep * 130}%, currentColor 100%)`,
    WebkitBackgroundClip: "text", backgroundClip: "text", WebkitTextFillColor: "transparent",
  } : {};
  return (
    <div style={{ ...style, ...shimmerStyle, letterSpacing: effect === "tracking" ? `${0.02 + (1 - trackP) * 0.45}em` : style?.letterSpacing }}>
      {rows}
      {caret && <span style={{ display: "inline-block", width: "0.08em", height: "0.9em", background: accent, verticalAlign: "-0.1em", marginLeft: "0.06em" }} />}
    </div>
  );
};
