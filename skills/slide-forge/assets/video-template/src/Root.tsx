import React from "react";
import { Composition } from "remotion";
import { Movie, movieDuration } from "./Movie";
import storyboard from "../storyboard.json";
import type { Storyboard } from "./types";

const sb = storyboard as unknown as Storyboard;
export const Root: React.FC = () => (
  <Composition id="Movie" component={Movie} durationInFrames={movieDuration(sb)} fps={sb.fps} width={sb.width} height={sb.height} defaultProps={{ sb }} />
);
