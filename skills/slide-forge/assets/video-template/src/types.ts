export type Style = { bg: string; fg: string; muted: string; accent: string; accent2?: string; glow: string; head: string; body: string; num: string; mono: string };

/** Transition INTO a scene (or the storyboard default). CSS types work in any Chromium;
    shader types need Chrome ≥ 149 (HTML-in-canvas) — video.py setup provides one. */
export type TransitionType =
  | "none" | "fade" | "slide" | "wipe" | "flip" | "clockWipe" | "iris" | "pushCut"
  | "crossZoom" | "blurSlide" | "zoomInOut" | "swap" | "dissolve" | "filmBurn" | "zoomBlur" | "linearBlur" | "dreamyZoom" | "ripple" | "crosswarp" | "bookFlip";
export type Transition = {
  type: TransitionType; seconds?: number;
  direction?: "from-left" | "from-right" | "from-top" | "from-bottom";
  timing?: "ease" | "linear" | "spring";
};
export type Overlay = { type: "lightLeak"; seconds?: number; seed?: number; hue?: number };

export type Scene = {
  type: "title" | "end" | "globe" | "photo" | "kinetic" | "stat" | "steps" | "bars" | "lottie";
  seconds: number;
  transition?: Transition;   // into this scene
  overlay?: Overlay;         // cut into this scene with a light leak over the cut (replaces the transition)
  motionBlur?: boolean;      // HTML-in-canvas motion blur for this scene (Chrome ≥ 149; not for globe)
} & Record<string, any>;

export type Storyboard = {
  title: string; fps: number; width: number; height: number;
  motion?: "calm" | "lively" | "punchy";
  transition?: Transition;
  sky?: string; lang?: string; fonts: string[]; style: Style; scenes: Scene[];
};
