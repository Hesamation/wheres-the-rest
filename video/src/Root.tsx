import React from "react";
import { Composition } from "remotion";

// Placeholder root: proves the bundler + renderer pipeline. Replaced by the real composition.
export const FPS = 30;
export const WIDTH = 1920;
export const HEIGHT = 1080;

const ToolchainSmoke: React.FC = () => (
  <div
    style={{
      background: "#161a1d",
      color: "#f2f4f8",
      fontFamily: "IBM Plex Sans, sans-serif",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      height: "100%",
      fontSize: 72,
    }}
  >
    Toolchain smoke {new Date(0).toISOString().slice(0, 10)}
  </div>
);

export const RemotionRoot: React.FC = () => (
  <Composition
    id="ToolchainSmoke"
    component={ToolchainSmoke}
    durationInFrames={FPS * 2}
    fps={FPS}
    width={WIDTH}
    height={HEIGHT}
  />
);
