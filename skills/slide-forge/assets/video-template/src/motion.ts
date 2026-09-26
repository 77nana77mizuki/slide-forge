/* Motion system: one vocabulary of easings, durations and staggers for the whole film.
   Pick a preset per storyboard ("motion": "calm" | "lively" | "punchy"); scenes read it via useMotion().
   Values follow IBM Carbon's expressive curves (enter decelerates, exit accelerates) and Remotion's
   spring easing; timings are in frames at 30 fps and scale with fps. */
import { createContext, useContext } from "react";
import { Easing, interpolate } from "remotion";

export type PresetName = "calm" | "lively" | "punchy";
type EaseFn = (t: number) => number;

export const EASE = {
  enter: Easing.bezier(0, 0, 0.3, 1),          // Carbon expressive entrance
  exit: Easing.bezier(0.4, 0.14, 1, 1),        // Carbon expressive exit
  standard: Easing.bezier(0.4, 0.14, 0.3, 1),  // Carbon expressive standard (A → B on screen)
  snap: Easing.bezier(0.16, 1, 0.3, 1),        // fast out, long settle
  settle: Easing.spring({ damping: 200 }),     // spring, no bounce
};

export type Motion = {
  name: PresetName;
  enter: EaseFn;          // entrances
  pop: EaseFn;            // scale-ins (may overshoot)
  dur: number;            // entrance duration, frames @30fps
  distance: number;       // travel for rise/slide, px
  staggerChar: number;    // frames between characters
  staggerWord: number;    // frames between words / phrases
  staggerLine: number;    // frames between lines
  countDur: number;       // count-up duration
  titleEffect: "rise" | "mask" | "slam" | "blur" | "pop" | "tracking" | "type" | "scramble" | "shimmer";  // default headline effect
};

export const PRESETS: Record<PresetName, Motion> = {
  calm:   { name: "calm",   enter: EASE.enter, pop: Easing.spring({ damping: 200 }), dur: 20, distance: 40, staggerChar: 1.6, staggerWord: 5, staggerLine: 10, countDur: 40, titleEffect: "rise" },
  lively: { name: "lively", enter: EASE.snap,  pop: Easing.spring({ damping: 14 }),  dur: 16, distance: 56, staggerChar: 1.2, staggerWord: 4, staggerLine: 8,  countDur: 32, titleEffect: "mask" },
  punchy: { name: "punchy", enter: EASE.snap,  pop: Easing.spring({ damping: 9 }),   dur: 11, distance: 80, staggerChar: 0.9, staggerWord: 3, staggerLine: 6,  countDur: 24, titleEffect: "slam" },
};

export const MotionCtx = createContext<{ m: Motion; fps: number }>({ m: PRESETS.calm, fps: 30 });
/** Motion preset with every frame count already scaled to the composition fps. */
export const useMotion = () => {
  const { m, fps } = useContext(MotionCtx);
  const k = fps / 30;
  return { ...m, dur: m.dur * k, staggerChar: m.staggerChar * k, staggerWord: m.staggerWord * k, staggerLine: m.staggerLine * k, countDur: m.countDur * k, fps };
};

/** Clamped tween from frame `start` over `dur` frames. */
export const tween = (f: number, start: number, dur: number, from = 0, to = 1, ease: EaseFn = EASE.enter) =>
  interpolate(f, [start, start + Math.max(1, dur)], [from, to], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: ease });

/** 0→1 progress, clamped. */
export const prog = (f: number, start: number, dur: number, ease: EaseFn = EASE.enter) => tween(f, start, dur, 0, 1, ease);

/** Scale that looks linear to the eye (Remotion's perceptual-scale output). */
export const pscale = (f: number, start: number, dur: number, from: number, to: number, ease: EaseFn) =>
  interpolate(f, [start, start + Math.max(1, dur)], [from, to], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: ease, output: "perceptual-scale" });
