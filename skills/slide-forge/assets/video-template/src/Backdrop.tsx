/* Backdrops for text-led scenes. Subtle, slow, deterministic (seeded noise), never competing with the text.
   stars · plain · mesh (drifting colour fields) · grid (fading engineering grid with a slow pan)
   dots (dot matrix with a travelling swell) · rays (slow light rays from the top) · <image path> */
import React from "react";
import { AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { ThreeCanvas } from "@remotion/three";
import { noise2D } from "@remotion/noise";
import { Starfield } from "./lib";
import type { Style } from "./types";

export type BackdropKind = "stars" | "plain" | "mesh" | "grid" | "dots" | "rays" | string;

const alpha = (hex: string, a: number) => (/^#[0-9a-f]{6}$/i.test(hex) ? hex + Math.round(a * 255).toString(16).padStart(2, "0") : hex);

export const Backdrop: React.FC<{ kind: BackdropKind; style: Style; sky?: string; seed?: number }> = ({ kind, style: S, sky, seed = 1 }) => {
  const f = useCurrentFrame();
  const { width, height, durationInFrames: D, fps } = useVideoConfig();
  if (kind === "stars") {
    const z = interpolate(f, [0, D], [9, 7.2]);
    return (
      <>
        <ThreeCanvas width={width} height={height} camera={{ position: [0, 0, z], fov: 45 }} gl={{ antialias: true }}>
          <Starfield frame={f + 400} sky={sky} />
        </ThreeCanvas>
        <AbsoluteFill style={{ background: `radial-gradient(1200px 700px at 30% 60%, ${S.glow}, transparent 70%)` }} />
      </>
    );
  }
  if (kind === "mesh") {
    const t = f / fps;
    const cols = [S.accent, S.accent2 ?? S.accent, S.fg];
    const blobs = cols.map((c, i) => {
      const x = 50 + 38 * noise2D(`${seed}x${i}`, t * 0.06, i * 3.1);
      const y = 50 + 34 * noise2D(`${seed}y${i}`, t * 0.06, i * 7.7);
      const r = 900 + 180 * noise2D(`${seed}r${i}`, t * 0.05, i);
      return `radial-gradient(${r}px ${r * 0.7}px at ${x}% ${y}%, ${alpha(c, i === 2 ? 0.05 : 0.2)}, transparent 70%)`;
    });
    return <AbsoluteFill style={{ background: [...blobs, S.bg].join(",") }} />;
  }
  if (kind === "grid") {
    const pan = (f / fps) * 6;
    const line = alpha(S.fg, 0.06);
    return (
      <AbsoluteFill style={{
        background: `radial-gradient(1100px 700px at 80% 0%, ${S.glow}, transparent 70%), linear-gradient(${line} 1px, transparent 1px) 0 ${pan}px / 80px 80px, linear-gradient(90deg, ${line} 1px, transparent 1px) ${pan}px 0 / 80px 80px, ${S.bg}`,
        maskImage: "linear-gradient(#000, rgba(0,0,0,.55))",
      }} />
    );
  }
  if (kind === "dots") {
    const t = f / fps;
    const cx = 50 + 30 * noise2D(`${seed}d`, t * 0.05, 0), cy = 50 + 25 * noise2D(`${seed}e`, 0, t * 0.05);
    const dot = alpha(S.fg, 0.16);
    return (
      <AbsoluteFill style={{ background: S.bg }}>
        <AbsoluteFill style={{ backgroundImage: `radial-gradient(${dot} 1.6px, transparent 1.8px)`, backgroundSize: "36px 36px",
          maskImage: `radial-gradient(900px 620px at ${cx}% ${cy}%, #000 0%, rgba(0,0,0,.25) 60%, transparent 100%)` }} />
        <AbsoluteFill style={{ background: `radial-gradient(900px 620px at ${cx}% ${cy}%, ${S.glow}, transparent 70%)` }} />
      </AbsoluteFill>
    );
  }
  if (kind === "rays") {
    const t = f / fps;
    const rays = Array.from({ length: 7 }, (_, i) => {
      const a = -38 + i * 12 + 4 * noise2D(`${seed}ray${i}`, t * 0.08, i);
      const o = 0.05 + 0.05 * (0.5 + 0.5 * noise2D(`${seed}op${i}`, t * 0.12, i));
      return `conic-gradient(from ${180 + a - 2}deg at 50% -10%, transparent 0deg, ${alpha(S.accent, o)} 2deg, transparent 4deg)`;
    });
    return <AbsoluteFill style={{ background: [...rays, `radial-gradient(1400px 800px at 50% -10%, ${S.glow}, transparent 70%)`, S.bg].join(","), filter: "blur(6px)" }} />;
  }
  if (kind === "plain") return <AbsoluteFill style={{ background: `radial-gradient(1200px 700px at 30% 60%, ${S.glow}, transparent 70%), ${S.bg}` }} />;
  return (
    <>
      <Img src={staticFile(kind)} style={{ width: "100%", height: "100%", objectFit: "cover", transform: `scale(${interpolate(f, [0, D], [1.06, 1])})` }} />
      <AbsoluteFill style={{ background: `color-mix(in srgb, ${S.bg} 72%, transparent)` }} />
    </>
  );
};
