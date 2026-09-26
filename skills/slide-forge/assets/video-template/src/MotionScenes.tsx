/* Motion-graphics scenes: kinetic statement · stat (ring / bar / big number) · steps (drawn connector) · bars (chart) · lottie.
   One hero motion per scene; supporting elements follow in speaking order (heading → hero → detail). */
import React, { useEffect, useState } from "react";
import { AbsoluteFill, cancelRender, continueRender, delayRender, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { evolvePath } from "@remotion/paths";
import { Lottie, type LottieAnimationData } from "@remotion/lottie";
import { Backdrop, type BackdropKind } from "./Backdrop";
import { buildFrames, KText, stripMarks, type By, type Effect } from "./Kinetic";
import { EASE, prog, pscale, useMotion } from "./motion";
import { CountUp, Credit, markColor, useRise } from "./Scenes";
import type { Style } from "./types";

type Base = { style: Style; sky?: string; lang?: string; kicker?: string; credit?: string; backdrop?: BackdropKind; effect?: Effect };
const Kicker: React.FC<{ text?: string; S: Style; st: React.CSSProperties }> = ({ text, S, st }) =>
  text ? <div style={{ ...st, font: `700 26px ${S.mono}`, letterSpacing: ".16em", color: S.accent, textTransform: "uppercase" }}>{text}</div> : null;
const alpha = (hex: string, a: number) => (/^#[0-9a-f]{6}$/i.test(hex) ? hex + Math.round(a * 255).toString(16).padStart(2, "0") : hex);

/** em-width estimate: full-width glyphs 1em, Latin ≈ .56em (deterministic; no DOM measuring needed) */
export const emWidth = (s: string) => Array.from(stripMarks(s)).reduce((a, c) => a + (c.charCodeAt(0) > 0x2e80 ? 1 : 0.56), 0);

/* ---------- kinetic: the statement IS the picture ---------- */
export type KineticProps = Base & { text: string; sub?: string; by?: By; align?: "left" | "center"; size?: number; exit?: boolean };
export const KineticScene: React.FC<KineticProps> = (p) => {
  const f = useCurrentFrame();
  const { durationInFrames: D, fps } = useVideoConfig();
  const m = useMotion(); const rise = useRise(); const S = p.style;
  const lines = p.text.split("\n");
  const maxEm = Math.max(...lines.map(emWidth), 1);
  const size = p.size ?? Math.round(Math.max(64, Math.min(180, 1560 / maxEm, 760 / (lines.length * 1.22))));
  const eff = p.effect ?? m.titleEffect;
  const t0 = p.kicker ? 10 : 4;
  const tEnd = t0 + buildFrames(p.text, p.by ?? (eff === "type" ? "char" : "phrase"), m, eff);
  const out = p.exit ? D - Math.round(fps * 0.7) : undefined;
  const subOut = out !== undefined ? 1 - prog(f, out, m.dur * 0.6, EASE.exit) : 1;
  const center = p.align === "center";
  return (
    <AbsoluteFill style={{ background: S.bg }}>
      <Backdrop kind={p.backdrop ?? "mesh"} style={S} sky={p.sky} />
      <AbsoluteFill lang={p.lang ?? "ja"} style={{ padding: "0 180px", justifyContent: "center", alignItems: center ? "center" : "flex-start", gap: 30 }}>
        <Kicker text={p.kicker} S={S} st={{ ...rise(f, 2), opacity: Number(rise(f, 2).opacity) * subOut }} />
        <KText text={p.text} start={t0} effect={eff} by={p.by} out={out} align={center ? "center" : "left"} accent={S.accent} markColor={markColor(S.accent)}
          style={{ font: `800 ${size}px/1.22 ${S.head}`, color: S.fg }} />
        {p.sub && <div style={{ ...rise(f, tEnd + m.dur * 0.3), opacity: Number(rise(f, tEnd + m.dur * 0.3).opacity) * subOut, font: `500 38px/1.6 ${S.body}`, color: S.muted, maxWidth: 1300, textAlign: center ? "center" : "left" }}>{p.sub}</div>}
      </AbsoluteFill>
      <Credit text={p.credit} style={S} left={180} />
    </AbsoluteFill>
  );
};

/* ---------- stat: one number, one visual that means the same thing ---------- */
export type StatProps = Base & { big: string; unit?: string; title: string; caption?: string; viz?: "ring" | "bar" | "none"; value?: number };
export const StatScene: React.FC<StatProps> = (p) => {
  const f = useCurrentFrame();
  const m = useMotion(); const rise = useRise(); const S = p.style;
  const eff = p.effect ?? "rise";
  const t0 = p.kicker ? 8 : 4;
  const tEnd = t0 + buildFrames(p.title, "phrase", m, eff);
  const v0 = tEnd - m.dur * 0.3, vd = m.countDur * 1.3;
  const pct = Math.max(0, Math.min(100, p.value ?? parseFloat(String(p.big).replace(/,/g, "")))) / 100;
  const pr = prog(f, v0, vd, EASE.snap) * pct;
  const viz = p.viz ?? (p.unit === "%" ? "ring" : "none");
  const number = (px: number) => (
    <div style={{ display: "flex", alignItems: "baseline", gap: px * 0.08, color: S.accent, font: `700 ${px}px/1 ${S.num}`, letterSpacing: "-.02em", fontVariantNumeric: "tabular-nums" }}>
      <CountUp value={p.big} start={v0} dur={vd} />{p.unit && <span style={{ fontSize: px * 0.38 }}>{p.unit}</span>}
    </div>
  );
  if (viz === "ring") {
    const R = 290, C = 2 * Math.PI * R, sw = 46;
    return (
      <AbsoluteFill style={{ background: S.bg }}>
        <Backdrop kind={p.backdrop ?? "grid"} style={S} sky={p.sky} />
        <svg width={1920} height={1080} style={{ position: "absolute", inset: 0 }}>
          <g transform="translate(1370 540) rotate(-90)">
            <circle r={R} fill="none" stroke={alpha(S.fg, 0.1)} strokeWidth={sw} style={{ opacity: prog(f, v0 - m.dur, m.dur) }} />
            <circle r={R} fill="none" stroke={S.accent} strokeWidth={sw} strokeLinecap="round" strokeDasharray={C} strokeDashoffset={C * (1 - pr)} style={{ opacity: pr > 0.001 ? 1 : 0 }} />
          </g>
        </svg>
        <div style={{ position: "absolute", left: 1370 - 260, top: 540 - 90, width: 520, height: 180, display: "flex", justifyContent: "center", alignItems: "center", scale: String(pscale(f, v0, m.dur * 1.6, 0.6, 1, m.pop)), opacity: prog(f, v0, m.dur * 0.6) } as React.CSSProperties}>{number(150)}</div>
        <AbsoluteFill lang={p.lang ?? "ja"} style={{ padding: "0 120px", justifyContent: "center", alignItems: "flex-start" }}>
          <div style={{ width: 760, display: "flex", flexDirection: "column", gap: 24 }}>
            <Kicker text={p.kicker} S={S} st={rise(f, 2)} />
            <KText text={p.title} start={t0} effect={eff} accent={S.accent} markColor={markColor(S.accent)} style={{ font: `800 68px/1.28 ${S.head}`, color: S.fg }} />
            {p.caption && <div style={{ ...rise(f, v0 + vd * 0.6), font: `500 34px/1.6 ${S.body}`, color: S.muted }}>{p.caption}</div>}
          </div>
        </AbsoluteFill>
        <Credit text={p.credit} style={S} />
      </AbsoluteFill>
    );
  }
  return (
    <AbsoluteFill style={{ background: S.bg }}>
      <Backdrop kind={p.backdrop ?? "grid"} style={S} sky={p.sky} />
      <AbsoluteFill lang={p.lang ?? "ja"} style={{ padding: "0 180px", justifyContent: "center", alignItems: "flex-start", gap: 26 }}>
        <Kicker text={p.kicker} S={S} st={rise(f, 2)} />
        <KText text={p.title} start={t0} effect={eff} accent={S.accent} markColor={markColor(S.accent)} style={{ font: `800 64px/1.3 ${S.head}`, color: S.fg, maxWidth: 1500 }} />
        <div style={{ scale: String(pscale(f, v0, m.dur * 1.6, 0.7, 1, m.pop)), transformOrigin: "left center", opacity: prog(f, v0, m.dur * 0.6) } as React.CSSProperties}>{number(240)}</div>
        {viz === "bar" && (
          <div style={{ width: 1500, height: 28, borderRadius: 14, background: alpha(S.fg, 0.1), overflow: "hidden", opacity: prog(f, v0 - m.dur * 0.5, m.dur) }}>
            <div style={{ width: `${pr * 100}%`, height: "100%", borderRadius: 14, background: S.accent }} />
          </div>
        )}
        {p.caption && <div style={{ ...rise(f, v0 + vd * 0.6), font: `500 36px/1.6 ${S.body}`, color: S.muted, maxWidth: 1400 }}>{p.caption}</div>}
      </AbsoluteFill>
      <Credit text={p.credit} style={S} left={180} />
    </AbsoluteFill>
  );
};

/* ---------- steps: a line draws itself and each step pops in as the line reaches it ---------- */
export type StepsProps = Base & { title: string; items: { title: string; text?: string }[] };
export const StepsScene: React.FC<StepsProps> = (p) => {
  const f = useCurrentFrame();
  const { durationInFrames: D } = useVideoConfig();
  const m = useMotion(); const rise = useRise(); const S = p.style;
  const n = Math.max(2, p.items.length);
  const x0 = 300, x1 = 1620, y = 560, gap = (x1 - x0) / (n - 1), badge = 92;
  const t0 = p.kicker ? 8 : 4;
  const lineStart = t0 + buildFrames(p.title, "phrase", m, p.effect ?? "rise") - m.dur * 0.4;
  const draw = Math.min(D * 0.42, (n - 1) * m.dur * 1.5 + m.dur);
  const d = `M ${x0} ${y} L ${x1} ${y}`;
  const lp = prog(f, lineStart, draw, EASE.standard);
  const ev = evolvePath(lp, d);
  const reach = (i: number) => lineStart + draw * EASE.standard(i / (n - 1)) * 0.98 - 3;   // approx. when the line tip hits step i
  const colW = Math.min(420, gap - 30);
  return (
    <AbsoluteFill style={{ background: S.bg }}>
      <Backdrop kind={p.backdrop ?? "grid"} style={S} sky={p.sky} />
      <AbsoluteFill lang={p.lang ?? "ja"} style={{ padding: "150px 180px 0", gap: 20 }}>
        <Kicker text={p.kicker} S={S} st={rise(f, 2)} />
        <KText text={p.title} start={t0} effect={p.effect ?? "rise"} accent={S.accent} markColor={markColor(S.accent)} style={{ font: `800 64px/1.3 ${S.head}`, color: S.fg, maxWidth: 1500 }} />
      </AbsoluteFill>
      <svg width={1920} height={1080} style={{ position: "absolute", inset: 0 }}>
        <path d={d} stroke={alpha(S.fg, 0.14)} strokeWidth={6} />
        <path d={d} stroke={S.accent} strokeWidth={6} strokeLinecap="round" strokeDasharray={ev.strokeDasharray} strokeDashoffset={ev.strokeDashoffset} style={{ opacity: lp > 0.001 ? 1 : 0 }} />
      </svg>
      {p.items.map((it, i) => {
        const x = x0 + gap * i, r = reach(i);
        const on = prog(f, r, m.dur * 0.5);
        return (
          <React.Fragment key={i}>
            <div style={{ position: "absolute", left: x - badge / 2, top: y - badge / 2, width: badge, height: badge, borderRadius: badge, background: S.accent, color: S.bg, display: "flex", alignItems: "center", justifyContent: "center", font: `700 40px ${S.num}`, opacity: on, scale: String(pscale(f, r, m.dur * 1.5, 0.2, 1, m.pop)) } as React.CSSProperties}>{i + 1}</div>
            <div lang={p.lang ?? "ja"} style={{ ...rise(f, r + 3), position: "absolute", left: x - colW / 2, top: y + badge / 2 + 34, width: colW, textAlign: "center" }}>
              <div style={{ font: `800 52px/1.3 ${S.head}`, color: S.fg, wordBreak: "auto-phrase", textWrap: "balance" } as React.CSSProperties}>{it.title}</div>
              {it.text && <div style={{ marginTop: 12, font: `500 32px/1.55 ${S.body}`, color: S.muted, wordBreak: "auto-phrase", textWrap: "balance" } as React.CSSProperties}>{it.text}</div>}
            </div>
          </React.Fragment>
        );
      })}
      <Credit text={p.credit} style={S} left={180} />
    </AbsoluteFill>
  );
};

/* ---------- bars: horizontal bar chart, bars grow in order, one highlighted ---------- */
export type BarsProps = Base & { title: string; items: { label: string; value: number; display?: string }[]; unit?: string; highlight?: number | string; max?: number; caption?: string };
export const BarsScene: React.FC<BarsProps> = (p) => {
  const f = useCurrentFrame();
  const m = useMotion(); const rise = useRise(); const S = p.style;
  const n = p.items.length;
  const max = p.max ?? Math.max(...p.items.map((i) => i.value)) * 1.08;
  const hi = typeof p.highlight === "string" ? p.items.findIndex((i) => i.label === p.highlight) : p.highlight ?? -1;
  const t0 = p.kicker ? 8 : 4;
  const g0 = t0 + buildFrames(p.title, "phrase", m, p.effect ?? "rise") - m.dur * 0.3;
  const rowH = Math.min(118, 560 / n), barH = rowH * 0.56, top = 380 - (p.caption ? 20 : 0);
  const labelW = 360, barX = 180 + labelW + 36, barW = 1920 - barX - 360;
  return (
    <AbsoluteFill style={{ background: S.bg }}>
      <Backdrop kind={p.backdrop ?? "grid"} style={S} sky={p.sky} />
      <AbsoluteFill lang={p.lang ?? "ja"} style={{ padding: "140px 180px 0", gap: 20 }}>
        <Kicker text={p.kicker} S={S} st={rise(f, 2)} />
        <KText text={p.title} start={t0} effect={p.effect ?? "rise"} accent={S.accent} markColor={markColor(S.accent)} style={{ font: `800 60px/1.3 ${S.head}`, color: S.fg, maxWidth: 1560 }} />
      </AbsoluteFill>
      {p.items.map((it, i) => {
        const s = g0 + i * m.staggerWord * 2;
        const gp = prog(f, s, m.countDur, EASE.snap);
        const yy = top + i * rowH;
        const isHi = i === hi;
        const w = (it.value / max) * barW * gp;
        return (
          <React.Fragment key={i}>
            <div lang={p.lang ?? "ja"} style={{ position: "absolute", left: 180, top: yy, width: labelW, height: barH, display: "flex", alignItems: "center", justifyContent: "flex-end", font: `${isHi ? 800 : 500} 34px ${S.body}`, color: isHi ? S.fg : S.muted, opacity: prog(f, s - m.dur * 0.5, m.dur) }}>{it.label}</div>
            <div style={{ position: "absolute", left: barX, top: yy, width: w, height: barH, borderRadius: 8, background: isHi ? S.accent : alpha(S.fg, 0.26) }} />
            <div style={{ position: "absolute", left: barX + w + 20, top: yy, height: barH, display: "flex", alignItems: "center", font: `700 ${isHi ? 44 : 36}px ${S.num}`, color: isHi ? S.accent : S.fg, opacity: prog(f, s, m.dur * 0.6), fontVariantNumeric: "tabular-nums" }}>
              <CountUp value={it.display ?? String(it.value)} start={s} dur={m.countDur} />{p.unit && <span style={{ fontSize: "0.6em", marginLeft: 6 }}>{p.unit}</span>}
            </div>
          </React.Fragment>
        );
      })}
      {p.caption && <div lang={p.lang ?? "ja"} style={{ ...rise(f, g0 + n * m.staggerWord * 2 + m.countDur * 0.6), position: "absolute", left: 180, top: top + n * rowH + 20, font: `500 30px/1.6 ${S.body}`, color: S.muted, maxWidth: 1500 }}>{p.caption}</div>}
      <Credit text={p.credit} style={S} left={180} />
    </AbsoluteFill>
  );
};

/* ---------- lottie: licensed vector animation beside a text column ---------- */
const useLottie = (src: string) => {
  const [data, setData] = useState<LottieAnimationData | null>(null);
  const [handle] = useState(() => delayRender(`lottie ${src}`, { timeoutInMilliseconds: 60000 }));
  useEffect(() => {
    fetch(staticFile(src)).then((r) => r.json()).then((j) => { setData(j); continueRender(handle); }).catch((e) => cancelRender(e));
  }, [src, handle]);
  return data;
};
export type LottieSceneProps = Base & { lottie: string; title: string; caption?: string; side?: "left" | "right"; loop?: boolean; speed?: number; size?: number };
export const LottieScene: React.FC<LottieSceneProps> = (p) => {
  const f = useCurrentFrame();
  const data = useLottie(p.lottie);
  const m = useMotion(); const rise = useRise(); const S = p.style;
  const textLeft = (p.side ?? "right") === "right";
  const size = p.size ?? 760;
  const t0 = p.kicker ? 8 : 4;
  const tEnd = t0 + buildFrames(p.title, "phrase", m, p.effect ?? "rise");
  return (
    <AbsoluteFill style={{ background: S.bg }}>
      <Backdrop kind={p.backdrop ?? "plain"} style={S} sky={p.sky} />
      <div style={{ position: "absolute", top: 540 - size / 2, [textLeft ? "right" : "left"]: 150, width: size, height: size, opacity: prog(f, 0, m.dur), scale: String(pscale(f, 0, m.dur * 1.4, 0.9, 1, EASE.settle)) } as React.CSSProperties}>
        {data && <Lottie animationData={data} loop={p.loop ?? true} playbackRate={p.speed ?? 1} style={{ width: size, height: size }} />}
      </div>
      <AbsoluteFill lang={p.lang ?? "ja"} style={{ padding: "0 120px", justifyContent: "center", alignItems: textLeft ? "flex-start" : "flex-end" }}>
        <div style={{ width: 800, display: "flex", flexDirection: "column", gap: 24 }}>
          <Kicker text={p.kicker} S={S} st={rise(f, 2)} />
          <KText text={p.title} start={t0} effect={p.effect ?? "rise"} accent={S.accent} markColor={markColor(S.accent)} style={{ font: `800 68px/1.28 ${S.head}`, color: S.fg }} />
          {p.caption && <div style={{ ...rise(f, tEnd), font: `500 34px/1.6 ${S.body}`, color: S.muted }}>{p.caption}</div>}
        </div>
      </AbsoluteFill>
      <Credit text={p.credit} style={S} />
    </AbsoluteFill>
  );
};

