import React from "react";
import { AbsoluteFill, interpolate, Solid, useCurrentFrame, useVideoConfig } from "remotion";
import { TransitionSeries, linearTiming, springTiming } from "@remotion/transitions";
import { fade } from "@remotion/transitions/fade";
import { slide } from "@remotion/transitions/slide";
import { wipe } from "@remotion/transitions/wipe";
import { flip } from "@remotion/transitions/flip";
import { clockWipe } from "@remotion/transitions/clock-wipe";
import { iris } from "@remotion/transitions/iris";
import { pushCut } from "@remotion/transitions/push-cut";
import { crossZoom } from "@remotion/transitions/cross-zoom";
import { blurSlide } from "@remotion/transitions/blur-slide";
import { zoomInOut } from "@remotion/transitions/zoom-in-out";
import { swap } from "@remotion/transitions/swap";
import { dissolve } from "@remotion/transitions/dissolve";
import { filmBurn } from "@remotion/transitions/film-burn";
import { zoomBlur } from "@remotion/transitions/zoom-blur";
import { linearBlur } from "@remotion/transitions/linear-blur";
import { dreamyZoom } from "@remotion/transitions/dreamy-zoom";
import { ripple } from "@remotion/transitions/ripple";
import { crosswarp } from "@remotion/transitions/crosswarp";
import { bookFlip } from "@remotion/transitions/book-flip";
import { lightLeak } from "@remotion/effects/light-leak";
import { HtmlInCanvasMotionBlur } from "@remotion/motion-blur";
import { Card, Fonts, Globe, Photo } from "./Scenes";
import { BarsScene, KineticScene, LottieScene, StatScene, StepsScene } from "./MotionScenes";
import { EASE, MotionCtx, PRESETS } from "./motion";
import defaults from "./defaults.json";
import type { Overlay, Scene, Storyboard, Transition } from "./types";

const frames = (sb: Storyboard, s: number) => Math.round(s * sb.fps);
const presetOf = (sb: Storyboard) => PRESETS[sb.motion ?? "calm"] ?? PRESETS.calm;
/** transition into scene i (i ≥ 1): scene override → storyboard default → motion preset default */
export const transitionInto = (sb: Storyboard, i: number): Transition =>
  ({ ...(defaults.transition as any)[sb.motion ?? "calm"], ...(sb.transition ?? {}), ...(sb.scenes[i].transition ?? {}) }) as Transition;
const overlapInto = (sb: Storyboard, i: number) => {
  if (sb.scenes[i].overlay) return 0;
  const t = transitionInto(sb, i);
  return t.type === "none" ? 0 : frames(sb, t.seconds ?? 0.5);
};
export const movieDuration = (sb: Storyboard) =>
  sb.scenes.reduce((a, s, i) => a + frames(sb, s.seconds) - (i ? overlapInto(sb, i) : 0), 0);

const presentation = (t: Transition, w: number, h: number): any => {
  const direction = t.direction;
  switch (t.type) {
    case "slide": return slide({ direction: direction ?? "from-right" });
    case "wipe": return wipe({ direction: direction ?? "from-left" });
    case "flip": return flip({ direction: direction ?? "from-right" });
    case "clockWipe": return clockWipe({ width: w, height: h });
    case "iris": return iris({ width: w, height: h });
    case "pushCut": return pushCut();
    case "crossZoom": return crossZoom({});
    case "blurSlide": return blurSlide({ direction: direction ?? "from-right" });
    case "zoomInOut": return zoomInOut({});
    case "swap": return swap({});
    case "dissolve": return dissolve({});
    case "filmBurn": return filmBurn({});
    case "zoomBlur": return zoomBlur({});
    case "linearBlur": return linearBlur({});
    case "dreamyZoom": return dreamyZoom({});
    case "ripple": return ripple({});
    case "crosswarp": return crosswarp({});
    case "bookFlip": return bookFlip({ direction: direction ?? "from-right" });
    default: return fade();
  }
};
const timing = (t: Transition, n: number) =>
  t.timing === "spring" ? springTiming({ config: { damping: 200 }, durationInFrames: n })
    : linearTiming({ durationInFrames: n, easing: t.timing === "linear" ? undefined : EASE.standard });

const LightLeak: React.FC<{ o: Overlay }> = ({ o }) => {
  const f = useCurrentFrame(); const { durationInFrames: D, width, height } = useVideoConfig();
  return <Solid width={width} height={height} effects={[lightLeak({ seed: o.seed ?? 0, hueShift: o.hue ?? 0, progress: interpolate(f, [0, D - 1], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }) })]} />;
};

const SceneBody: React.FC<{ s: Scene; sb: Storyboard }> = ({ s, sb }) => {
  const { type, seconds, transition, overlay, motionBlur, ...props } = s as any;
  const common = { style: sb.style, sky: sb.sky, lang: sb.lang };
  const body = (() => {
    switch (type) {
      case "globe": return <Globe {...props} {...common} />;
      case "photo": return <Photo {...props} {...common} />;
      case "kinetic": return <KineticScene {...props} {...common} />;
      case "stat": return <StatScene {...props} {...common} />;
      case "steps": return <StepsScene {...props} {...common} />;
      case "bars": return <BarsScene {...props} {...common} />;
      case "lottie": return <LottieScene {...props} {...common} />;
      default: return <Card {...props} {...common} />;
    }
  })();
  if (!motionBlur || type === "globe") return body;
  return <HtmlInCanvasMotionBlur width={sb.width} height={sb.height} samples={6} shutterAngle={180}>{body}</HtmlInCanvasMotionBlur>;
};

export const Movie: React.FC<{ sb: Storyboard }> = ({ sb }) => {
  const items: React.ReactNode[] = [];
  sb.scenes.forEach((s, i) => {
    if (i > 0) {
      if (s.overlay) {
        items.push(<TransitionSeries.Overlay key={`o${i}`} durationInFrames={frames(sb, s.overlay.seconds ?? 1)}><LightLeak o={s.overlay} /></TransitionSeries.Overlay>);
      } else {
        const t = transitionInto(sb, i);
        if (t.type !== "none") items.push(<TransitionSeries.Transition key={`t${i}`} presentation={presentation(t, sb.width, sb.height)} timing={timing(t, frames(sb, t.seconds ?? 0.5))} />);
      }
    }
    items.push(<TransitionSeries.Sequence key={`s${i}`} durationInFrames={frames(sb, s.seconds)}><SceneBody s={s} sb={sb} /></TransitionSeries.Sequence>);
  });
  return (
    <MotionCtx.Provider value={{ m: presetOf(sb), fps: sb.fps }}>
      <AbsoluteFill style={{ background: sb.style.bg }}>
        <Fonts families={sb.fonts} />
        <TransitionSeries>{items}</TransitionSeries>
      </AbsoluteFill>
    </MotionCtx.Provider>
  );
};
