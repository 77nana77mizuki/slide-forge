/* Scene components. Text is HTML over the 3D canvas; motion is frame-driven and eased. */
import React, { useEffect, useState } from "react";
import { AbsoluteFill, continueRender, delayRender, Img, interpolate, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { ThreeCanvas } from "@remotion/three";
import { Atmosphere, easeInOut, Ring, Starfield, useTexture } from "./lib";
import { EASE, prog, useMotion } from "./motion";
import { buildFrames, KText, type Effect } from "./Kinetic";
import { Backdrop, type BackdropKind } from "./Backdrop";
import type { Style } from "./types";

/* ---------- fonts: one embedded CSS file (subset to the storyboard text by video.py) ---------- */
export const Fonts: React.FC<{ families: string[] }> = ({ families }) => {
  const [css, setCss] = useState("");
  const [handle] = useState(() => delayRender("fonts", { timeoutInMilliseconds: 60000 }));
  useEffect(() => {
    fetch(staticFile("fonts.css")).then((r) => (r.ok ? r.text() : "")).then(async (t) => {
      setCss(t);
      await new Promise((r) => setTimeout(r, 0));
      try { await Promise.all(families.map((f) => document.fonts.load(`700 40px "${f}"`, "あA1"))); await document.fonts.ready; } catch (e) { console.warn(e); }
      continueRender(handle);
    }).catch(() => continueRender(handle));
  }, [handle, families]);
  return <style>{css}</style>;
};

/* ---------- text helpers (all timing from the motion preset) ---------- */
export const useRise = () => {
  const m = useMotion();
  return (f: number, start: number, dur = m.dur) => {
    const t = prog(f, start, dur, m.enter);
    return { opacity: t, translate: `0 ${(1 - t) * m.distance * 0.7}px` } as React.CSSProperties;
  };
};
export const CountUp: React.FC<{ value: string; start: number; dur?: number }> = ({ value, start, dur }) => {
  const f = useCurrentFrame();
  const mo = useMotion();
  const m = value.match(/-?[\d,]*\.?\d+/);
  if (!m) return <>{value}</>;
  const target = parseFloat(m[0].replace(/,/g, "")), dec = (m[0].split(".")[1] || "").length, comma = m[0].includes(",");
  const v = target * prog(f, start, dur ?? mo.countDur, EASE.snap);
  const s = comma ? v.toLocaleString("en-US", { minimumFractionDigits: dec, maximumFractionDigits: dec }) : v.toFixed(dec);
  return <>{value.slice(0, m.index)}{s}{value.slice((m.index || 0) + m[0].length)}</>;
};
export const Credit: React.FC<{ text?: string; style: Style; left?: number }> = ({ text, style: S, left = 120 }) =>
  text ? <div style={{ position: "absolute", left, bottom: 54, font: `500 22px ${S.body}`, color: S.muted, opacity: 0.9 }}>{text}</div> : null;
export const markColor = (hex: string) => (/^#[0-9a-f]{6}$/i.test(hex) ? `${hex}5c` : hex);

/* ---------- shared text column (kicker → claim → big number → caption), staged in speaking order ---------- */
type TextProps = { kicker?: string; title: string; big?: string; unit?: string; caption?: string; style: Style; lang?: string; effect?: Effect };
const TextColumn: React.FC<TextProps & { f: number; textLeft: boolean }> = (p) => {
  const S = p.style, f = p.f;
  const rise = useRise();
  const m = useMotion();
  const tStart = 10, tEnd = tStart + buildFrames(p.title, "phrase", m, p.effect ?? "rise");
  return (
    <AbsoluteFill lang={p.lang ?? "ja"} style={{ padding: "0 120px", justifyContent: "center", alignItems: p.textLeft ? "flex-start" : "flex-end" }}>
      <div style={{ width: 760, display: "flex", flexDirection: "column", gap: 22, textAlign: "left" }}>
        {p.kicker && <div style={{ ...rise(f, 4), font: `700 26px ${S.mono}`, letterSpacing: ".16em", color: S.accent, textTransform: "uppercase" }}>{p.kicker}</div>}
        <KText text={p.title} start={tStart} effect={p.effect ?? "rise"} accent={S.accent} markColor={markColor(S.accent)} style={{ font: `800 66px/1.28 ${S.head}`, color: S.fg }} />
        {p.big && (
          <div style={{ ...rise(f, tEnd - m.dur * 0.4), display: "flex", alignItems: "baseline", gap: 14, color: S.accent, font: `700 150px/1 ${S.num}`, letterSpacing: "-.02em", fontVariantNumeric: "tabular-nums" }}>
            <CountUp value={p.big} start={tEnd - m.dur * 0.2} />{p.unit && <span style={{ fontSize: 56 }}>{p.unit}</span>}
          </div>
        )}
        {p.caption && <div style={{ ...rise(f, tEnd + (p.big ? m.dur : 0)), font: `500 34px/1.6 ${S.body}`, color: S.muted }}>{p.caption}</div>}
      </div>
    </AbsoluteFill>
  );
};

export type GlobeProps = {
  texture: string; kicker?: string; title: string; big?: string; unit?: string; caption?: string; credit?: string;
  side?: "left" | "right"; radius?: number; tilt?: number; spin?: number; glow?: string; glowStrength?: number;
  ring?: boolean; sunAngle?: number; style: Style; sky?: string; lang?: string;
} & TextProps;

/* ---------- Globe: textured sphere, sunlight, rim glow, optional ring, camera dolly ---------- */
export const Globe: React.FC<GlobeProps> = (p) => {
  const f = useCurrentFrame();
  const { width, height, durationInFrames: D } = useVideoConfig();
  const tex = useTexture(p.texture);
  const R = p.radius ?? (p.ring ? 1.05 : 1.45);   // ringed globes are smaller so the ring stays in frame
  const textLeft = (p.side ?? "right") === "right";          // planet on the right → text on the left
  const t = f / D;
  const camZ = interpolate(easeInOut(t), [0, 1], [8.6, 6.5]);   // slow dolly-in (ends with the whole globe in frame)
  const camX = interpolate(easeInOut(t), [0, 1], [textLeft ? -0.35 : 0.35, 0]);
  const spin = (p.spin ?? 40) * (Math.PI / 180) * (f / 30);     // degrees per second → radians at this frame
  const px = (textLeft ? 1 : -1) * (p.ring ? 2.2 : 1.55);   // ringed globes sit further out so the ring clears the text
  const sun = ((p.sunAngle ?? (textLeft ? 200 : -20)) * Math.PI) / 180;
  const S = p.style;
  return (
    <AbsoluteFill style={{ background: S.bg }}>
      <ThreeCanvas width={width} height={height} camera={{ position: [camX, 0.15, camZ], fov: 38 }} gl={{ antialias: true, preserveDrawingBuffer: true }}>
        <Starfield frame={f} sky={p.sky} />
        <ambientLight intensity={0.05} />
        <directionalLight position={[Math.cos(sun) * 10, 2.5, Math.sin(sun) * 10 + 4]} intensity={2.8} />
        <group position={[px, 0, 0]} rotation={[0, 0, ((p.tilt ?? 0) * Math.PI) / 180]}>
          {tex && (
            <mesh rotation={[0, spin, 0]}>
              <sphereGeometry args={[R, 128, 96]} />
              <meshStandardMaterial map={tex} roughness={1} metalness={0} />
            </mesh>
          )}
          {p.glow && <Atmosphere radius={R} color={p.glow} strength={p.glowStrength ?? 1.1} />}
          {p.ring && <group rotation={[0.38, 0, 0]}><Ring inner={R * 1.25} outer={R * 2.1} /></group>}
        </group>
      </ThreeCanvas>
      <TextColumn {...p} f={f} textLeft={textLeft} />
      <Credit text={p.credit} style={S} />
    </AbsoluteFill>
  );
};


/* ---------- Photo: still image with a slow Ken Burns move + scrim on the text side ---------- */
export type PhotoProps = TextProps & {
  image: string; credit?: string; side?: "left" | "right"; zoom?: [number, number]; focus?: [number, number]; scrim?: number;
};
export const Photo: React.FC<PhotoProps> = (p) => {
  const f = useCurrentFrame();
  const { durationInFrames: D } = useVideoConfig();
  const S = p.style;
  const textLeft = (p.side ?? "right") === "right";           // subject on the right → text on the left
  const [z0, z1] = p.zoom ?? [1.0, 1.08];
  const [fx, fy] = p.focus ?? [textLeft ? 0.65 : 0.35, 0.5];  // zoom toward the subject (0..1 of the frame)
  const z = interpolate(easeInOut(f / D), [0, 1], [z0, z1]);
  const a = p.scrim ?? 0.82;
  const dir = textLeft ? "90deg" : "270deg";
  return (
    <AbsoluteFill style={{ background: S.bg, overflow: "hidden" }}>
      <Img src={staticFile(p.image)} style={{ width: "100%", height: "100%", objectFit: "cover", transform: `scale(${z})`, transformOrigin: `${fx * 100}% ${fy * 100}%` }} />
      <AbsoluteFill style={{ background: `linear-gradient(${dir}, color-mix(in srgb, ${S.bg} ${a * 100}%, transparent) 0%, color-mix(in srgb, ${S.bg} ${a * 70}%, transparent) 38%, transparent 68%)` }} />
      <AbsoluteFill style={{ background: `linear-gradient(0deg, color-mix(in srgb, ${S.bg} 70%, transparent), transparent 22%)` }} />
      <TextColumn {...p} f={f} textLeft={textLeft} />
      <Credit text={p.credit} style={S} />
    </AbsoluteFill>
  );
};

/* ---------- Title / End: backdrop + kinetic headline ---------- */
export type CardProps = { kicker?: string; title: string; sub?: string; credit?: string; style: Style; sky?: string; lang?: string;
  backdrop?: BackdropKind; effect?: Effect };
export const Card: React.FC<CardProps> = (p) => {
  const f = useCurrentFrame();
  const S = p.style;
  const rise = useRise();
  const m = useMotion();
  const eff = p.effect ?? m.titleEffect;
  const tEnd = 10 + buildFrames(p.title, "phrase", m, eff);
  return (
    <AbsoluteFill style={{ background: S.bg }}>
      <Backdrop kind={p.backdrop ?? "stars"} style={S} sky={p.sky} />
      <AbsoluteFill lang={p.lang ?? "ja"} style={{ padding: "0 160px", justifyContent: "center", gap: 28 }}>
        {p.kicker && <div style={{ ...rise(f, 4), font: `700 28px ${S.mono}`, letterSpacing: ".18em", color: S.accent, textTransform: "uppercase" }}>{p.kicker}</div>}
        <KText text={p.title} start={10} effect={eff} accent={S.accent} markColor={markColor(S.accent)} style={{ font: `800 112px/1.18 ${S.head}`, color: S.fg, maxWidth: 1400 }} />
        {p.sub && <div style={{ ...rise(f, tEnd), font: `500 40px/1.6 ${S.body}`, color: S.muted, maxWidth: 1200 }}>{p.sub}</div>}
      </AbsoluteFill>
      <Credit text={p.credit} style={S} left={160} />
    </AbsoluteFill>
  );
};
