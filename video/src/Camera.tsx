import React from "react";
import { Img, OffthreadVideo, Sequence, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { interpolate } from "remotion";

// Smooth camera between keyframes {t (sec), s (scale), cx, cy (layout px)}.
export const useCamera = (frames) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  if (!frames || frames.length === 0) return { s: 1, cx: 960, cy: 540 };
  if (t <= frames[0].t) return { s: frames[0].s, cx: frames[0].cx, cy: frames[0].cy };
  for (let i = 0; i < frames.length - 1; i++) {
    const A = frames[i], B = frames[i + 1];
    if (t >= A.t && t <= B.t) {
      const dur = Math.max(B.t - A.t, 0.001);
      const raw = (t - A.t) / dur;
      const e = raw * raw * (3 - 2 * raw); // smoothstep
      return {
        s: A.s + (B.s - A.s) * e,
        cx: A.cx + (B.cx - A.cx) * e,
        cy: A.cy + (B.cy - A.cy) * e,
      };
    }
  }
  const L = frames[frames.length - 1];
  return { s: L.s, cx: L.cx, cy: L.cy };
};

// Full-frame pan/zoom wrapper for a 1920x1080-native base (stills are 2x, handled by CSS size).
export const PanZoom: React.FC<{
  cam: { s: number; cx: number; cy: number };
  children: React.ReactNode;
}> = ({ cam, children }) => {
  const W = 1920, H = 1080;
  // keep the viewport inside the frame at every scale
  const s = Math.max(cam.s, 1);
  const cx = Math.min(Math.max(cam.cx, W / (2 * s)), W - W / (2 * s));
  const cy = Math.min(Math.max(cam.cy, H / (2 * s)), H - H / (2 * s));
  return (
    <div style={{ position: "absolute", inset: 0, overflow: "hidden", background: "#0d0f11" }}>
      <div
        style={{
          position: "absolute",
          width: W,
          height: H,
          transformOrigin: "0 0",
          transform: `translate(${W / 2 - cx * s}px, ${H / 2 - cy * s}px) scale(${s})`,
        }}
      >
        {children}
      </div>
    </div>
  );
};

export const BaseStill: React.FC<{ name: string }> = ({ name }) => (
  <Img src={staticFile(`stills/${name}.png`)} style={{ width: 1920, height: 1080, display: "block" }} />
);

// Clip window: plays clips/[name].mp4 from fromSec to toSec during film seconds [a, b).
// The Sequence anchors media time to the film timeline; without it, OffthreadVideo
// would offset from the composition start and seek past the clip end.
export const ClipWindow: React.FC<{
  name: string;
  a: number;
  b: number;
  fromSec: number;
  toSec?: number;
}> = ({ name, a, b, fromSec, toSec }) => {
  const { fps } = useVideoConfig();
  return (
    <Sequence from={Math.round(a * fps)} durationInFrames={Math.max(1, Math.round((b - a) * fps))}>
      <OffthreadVideo
        src={staticFile(`clips/${name}.mp4`)}
        startFrom={Math.round(fromSec * fps)}
        {...(toSec != null ? { endAt: Math.round(toSec * fps) } : {})}
        style={{ width: 1920, height: 1080, display: "block" }}
      />
    </Sequence>
  );
};

// Gentle fade helper for scene seams
export const useFade = (a: number, b: number, dur = 0.3) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const fin = interpolate(t, [a, a + dur], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const fout = interpolate(t, [b - dur, b], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return Math.min(fin, fout);
};
