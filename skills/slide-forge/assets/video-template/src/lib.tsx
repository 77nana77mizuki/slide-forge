/* Shared building blocks: deterministic helpers, async textures, starfield, globe, rings.
   RULE: every animated value derives from useCurrentFrame() (never clocks / useFrame / Math.random),
   so any frame renders identically on any machine, in any order, in parallel. */
import React, { useEffect, useMemo, useState } from "react";
import { continueRender, delayRender, staticFile } from "remotion";
import {
  AdditiveBlending, BackSide, BufferAttribute, BufferGeometry, CanvasTexture, Color, DoubleSide,
  RingGeometry, SRGBColorSpace, Texture, TextureLoader, Vector3,
} from "three";

/* ---------- deterministic randomness ---------- */
export const mulberry32 = (seed: number) => () => {
  seed |= 0; seed = (seed + 0x6d2b79f5) | 0;
  let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
  t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
};

/* ---------- textures: block rendering until loaded ---------- */
const cache = new Map<string, Promise<Texture>>();
const loadTex = (src: string) => {
  if (!cache.has(src)) {
    cache.set(src, new Promise((res, rej) =>
      new TextureLoader().load(staticFile(src), (t) => { t.colorSpace = SRGBColorSpace; t.anisotropy = 8; res(t); }, undefined, rej)));
  }
  return cache.get(src)!;
};
export const useTexture = (src?: string) => {
  const [tex, setTex] = useState<Texture | null>(null);
  const [handle] = useState(() => (src ? delayRender(`texture ${src}`, { timeoutInMilliseconds: 60000 }) : null));
  useEffect(() => {
    if (!src || handle === null) return;
    loadTex(src).then((t) => { setTex(t); continueRender(handle); })
      .catch((e) => { console.error(`texture failed: ${src}`, e); continueRender(handle); });
  }, [src, handle]);
  return tex;
};

/* ---------- starfield: sharp points at any resolution + optional faint sky map ---------- */
export const Starfield: React.FC<{ frame: number; seed?: number; count?: number; sky?: string; skyOpacity?: number }> = ({
  frame, seed = 7, count = 5000, sky, skyOpacity = 0.35,
}) => {
  const geo = useMemo(() => {
    const r = mulberry32(seed);
    const pos = new Float32Array(count * 3), col = new Float32Array(count * 3);
    const tints = [new Color("#ffffff"), new Color("#cfe0ff"), new Color("#ffe9c4"), new Color("#ffd2b0")];
    for (let i = 0; i < count; i++) {
      const u = r() * 2 - 1, th = r() * Math.PI * 2, rad = 60 + r() * 20;
      const s = Math.sqrt(1 - u * u);
      pos.set([rad * s * Math.cos(th), rad * u, rad * s * Math.sin(th)], i * 3);
      const c = tints[Math.floor(r() * tints.length)].clone().multiplyScalar(0.35 + Math.pow(r(), 3) * 0.9);
      col.set([c.r, c.g, c.b], i * 3);
    }
    const g = new BufferGeometry();
    g.setAttribute("position", new BufferAttribute(pos, 3));
    g.setAttribute("color", new BufferAttribute(col, 3));
    return g;
  }, [seed, count]);
  const skyTex = useTexture(sky);
  const rot = frame * 0.00035;
  return (
    <group rotation={[0.25, rot, 0.08]}>
      <points geometry={geo}>
        <pointsMaterial size={0.16} sizeAttenuation vertexColors transparent depthWrite={false} />
      </points>
      {skyTex && (
        <mesh>
          <sphereGeometry args={[90, 64, 32]} />
          <meshBasicMaterial map={skyTex} side={BackSide} transparent opacity={skyOpacity} depthWrite={false} />
        </mesh>
      )}
    </group>
  );
};

/* ---------- atmosphere rim (fresnel) ---------- */
const rimVert = `varying vec3 vN; varying vec3 vV;
void main(){ vec4 mv = modelViewMatrix * vec4(position,1.0); vN = normalize(normalMatrix * normal); vV = normalize(-mv.xyz); gl_Position = projectionMatrix * mv; }`;
const rimFrag = `uniform vec3 uColor; uniform float uPower; uniform float uStrength; varying vec3 vN; varying vec3 vV;
void main(){ float f = pow(1.0 - max(dot(vN, vV), 0.0), uPower); gl_FragColor = vec4(uColor * f * uStrength, f * uStrength); }`;

export const Atmosphere: React.FC<{ radius: number; color: string; strength?: number }> = ({ radius, color, strength = 1.2 }) => {
  const uniforms = useMemo(() => ({ uColor: { value: new Color(color) }, uPower: { value: 3.2 }, uStrength: { value: strength } }), [color, strength]);
  return (
    <mesh scale={1.035}>
      <sphereGeometry args={[radius, 96, 64]} />
      <shaderMaterial vertexShader={rimVert} fragmentShader={rimFrag} uniforms={uniforms} transparent blending={AdditiveBlending} depthWrite={false} />
    </mesh>
  );
};

/* ---------- procedural ring (Saturn-like): radial bands from a seeded canvas ---------- */
const ringTexture = (seed: number) => {
  const c = document.createElement("canvas"); c.width = 1024; c.height = 4;
  const g = c.getContext("2d")!; const r = mulberry32(seed);
  for (let x = 0; x < c.width; x++) {
    const t = x / c.width;
    const gap = t > 0.62 && t < 0.66 ? 0.08 : 1;             // Cassini-division-like gap
    const band = 0.55 + 0.45 * Math.sin(t * 90 + r() * 0.8) * Math.sin(t * 23);
    const a = Math.max(0, Math.min(1, (0.35 + 0.6 * band) * gap * Math.min(1, t * 6) * Math.min(1, (1 - t) * 5)));
    const l = 190 + Math.floor(40 * band);
    g.fillStyle = `rgba(${l},${l - 18},${l - 48},${a})`; g.fillRect(x, 0, 1, 4);
  }
  const t = new CanvasTexture(c); t.colorSpace = SRGBColorSpace; return t;
};
export const Ring: React.FC<{ inner: number; outer: number; seed?: number }> = ({ inner, outer, seed = 3 }) => {
  const { geo, tex } = useMemo(() => {
    const geo = new RingGeometry(inner, outer, 256, 1);
    const p = geo.attributes.position as BufferAttribute, uv = geo.attributes.uv as BufferAttribute, v = new Vector3();
    for (let i = 0; i < p.count; i++) { v.fromBufferAttribute(p, i); uv.setXY(i, (v.length() - inner) / (outer - inner), 0.5); }
    return { geo, tex: ringTexture(seed) };
  }, [inner, outer, seed]);
  return (
    <mesh geometry={geo} rotation={[-Math.PI / 2, 0, 0]}>
      {/* unlit: a thin ring seen near edge-on gets almost no light from a standard material */}
      <meshBasicMaterial map={tex} side={DoubleSide} transparent depthWrite={false} color="#d8ccb4" />
    </mesh>
  );
};

/* ---------- easing ---------- */
export const easeOutCubic = (t: number) => 1 - Math.pow(1 - t, 3);
export const easeInOut = (t: number) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
export const clamp01 = (t: number) => Math.max(0, Math.min(1, t));
