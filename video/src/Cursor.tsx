import React from "react";
import { interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { COLORS } from "./theme";

export type CursorWaypoint = { t: number; x: number; y: number; click?: number };

// Editorial cursor: soft dot + ring with a click ripple, following waypoints in layout px.
export const CursorLayer: React.FC<{ waypoints: CursorWaypoint[]; visibleFrom: number; visibleTo: number }> = ({
  waypoints,
  visibleFrom,
  visibleTo,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;

  if (waypoints.length === 0) return null;

  // position: piecewise between waypoints with smooth ease
  let x = waypoints[0].x, y = waypoints[0].y;
  for (let i = 0; i < waypoints.length - 1; i++) {
    const A = waypoints[i], B = waypoints[i + 1];
    if (t >= A.t && t <= B.t) {
      const raw = (t - A.t) / Math.max(B.t - A.t, 0.001);
      const e = raw * raw * (3 - 2 * raw);
      x = A.x + (B.x - A.x) * e;
      y = A.y + (B.y - A.y) * e;
      break;
    }
  }
  const last = waypoints[waypoints.length - 1];
  if (t > last.t) { x = last.x; y = last.y; }

  const opacity = interpolate(
    t,
    [visibleFrom, visibleFrom + 0.25, visibleTo - 0.25, visibleTo],
    [0, 1, 1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );
  if (opacity <= 0) return null;

  // nearest click event
  const click = waypoints.find((w) => w.click != null)?.click ?? null;
  let ripple = 0;
  if (click != null) {
    ripple = interpolate(t, [click, click + 0.5], [0, 1], {
      extrapolateLeft: "clamp", extrapolateRight: "clamp",
    });
  }
  const press = click != null && t >= click && t <= click + 0.12 ? 1 : 0;

  return (
    <div style={{ position: "absolute", left: 0, top: 0, width: 1920, height: 1080, pointerEvents: "none", opacity }}>
      {click != null && ripple > 0 && ripple < 1 && (
        <div
          style={{
            position: "absolute",
            left: x - 30, top: y - 30, width: 60, height: 60, borderRadius: 30,
            border: `2.5px solid ${COLORS.blue}`,
            transform: `scale(${0.4 + ripple * 1.8})`,
            opacity: 1 - ripple,
          }}
        />
      )}
      <div
        style={{
          position: "absolute",
          left: x - (9 + press * 2), top: y - (9 + press * 2),
          width: 18 + press * 4, height: 18 + press * 4, borderRadius: "50%",
          background: COLORS.blue,
          boxShadow: `0 0 0 ${4 - press * 2}px rgba(76,141,255,0.35), 0 2px 10px rgba(0,0,0,0.45)`,
        }}
      />
    </div>
  );
};
