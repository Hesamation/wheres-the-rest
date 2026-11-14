import React from "react";
import { interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { COLORS, FONT } from "./theme";
import type { Caption } from "./types";

// Lower-third caption bar; hidden while a full-frame card shows the same words.
export const CaptionBar: React.FC<{ captions: Caption[] }> = ({ captions }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;

  const active = captions.find((c) => t >= c.a && t <= c.b);
  if (!active) return null;
  const opacity = Math.min(
    interpolate(t, [active.a, active.a + 0.18], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }),
    interpolate(t, [active.b - 0.18, active.b], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }),
  );
  if (active.onCard || opacity <= 0) return null;

  return (
    <div
      style={{
        position: "absolute", left: 0, right: 0, bottom: 44, opacity,
        display: "flex", justifyContent: "center", pointerEvents: "none",
      }}
    >
      <div
        style={{
          background: "rgba(13,15,17,0.86)", border: `1px solid ${COLORS.border}`, borderRadius: 10,
          padding: "16px 34px", maxWidth: 1560,
          fontFamily: FONT.sans, fontSize: 37, lineHeight: 1.35, color: COLORS.text,
          textAlign: "center",
        }}
      >
        {active.text}
      </div>
    </div>
  );
};
