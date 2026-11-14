import React from "react";
import { Composition } from "remotion";
import { Film } from "./Film";
import manifest from "./manifest.json";
import { loadFonts } from "./load-fonts";

loadFonts();

export const RemotionRoot: React.FC = () => (
  <Composition
    id="WheresTheRest"
    component={Film}
    durationInFrames={manifest.durationInFrames}
    fps={manifest.fps}
    width={manifest.width}
    height={manifest.height}
  />
);
