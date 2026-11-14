import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { COLORS, FONT } from "./theme";

const Frame: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div
    style={{
      position: "absolute",
      inset: 0,
      background: `radial-gradient(1400px 900px at 50% 42%, #1b2024 0%, ${COLORS.bgDeep} 70%)`,
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      justifyContent: "center",
      fontFamily: FONT.sans,
      color: COLORS.text,
    }}
  >
    {children}
  </div>
);

const rise = (delay: number, fps: number, frame: number) => {
  const s = spring({ frame: frame - delay * fps, fps, config: { damping: 200, stiffness: 90 }, durationInFrames: 24 });
  return { transform: `translateY(${(1 - s) * 26}px)`, opacity: s };
};

export const TitleCard: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  return (
    <Frame>
      <div style={{ ...rise(0.05, fps, frame), fontSize: 128, fontWeight: 640, letterSpacing: "-0.02em" }}>
        Executed.
      </div>
      <div style={{ ...rise(0.35, fps, frame), marginTop: 26, width: 132, height: 5, background: COLORS.blue, borderRadius: 3 }} />
    </Frame>
  );
};

export const RevealCard: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const inA = spring({ frame: frame - 0.0 * fps, fps, config: { damping: 200 }, durationInFrames: 20 });
  const q = rise(0.85, fps, frame);
  return (
    <Frame>
      <div
        style={{
          opacity: inA,
          display: "flex", gap: 44, alignItems: "center",
          fontFamily: FONT.mono, fontSize: 40, color: COLORS.textDim,
        }}
      >
        <div><b style={{ color: COLORS.text, fontSize: 56 }}>3</b> burns</div>
        <div style={{ color: COLORS.border }}>·</div>
        <div><b style={{ color: COLORS.green, fontSize: 56 }}>1</b> observed</div>
        <div style={{ color: COLORS.border }}>·</div>
        <div><b style={{ color: COLORS.red, fontSize: 56 }}>2</b> unrecorded</div>
      </div>
      <div style={{ ...q, marginTop: 54, fontSize: 118, fontWeight: 640, letterSpacing: "-0.02em", textAlign: "center" }}>
        Where&rsquo;s the rest?
      </div>
    </Frame>
  );
};

export const FutureCard: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const a = rise(0.0, fps, frame);
  const b = rise(0.5, fps, frame);
  const Row: React.FC<{ label: string; children: React.ReactNode; style?: React.CSSProperties }> = ({ label, children, style }) => (
    <div style={{ display: "flex", alignItems: "baseline", gap: 34, ...style }}>
      <div style={{
        fontFamily: FONT.mono, fontSize: 30, letterSpacing: "0.14em", textTransform: "uppercase",
        color: COLORS.textDim, minWidth: 210, textAlign: "right",
      }}>{label}</div>
      <div style={{ fontSize: 52, fontWeight: 600 }}>{children}</div>
    </div>
  );
  return (
    <Frame>
      <div style={a}>
        <Row label="Today">
          One public <span style={{ color: COLORS.blue }}>NEAR → Base</span> USDC route
        </Row>
      </div>
      <div style={{ ...b, marginTop: 60 }}>
        <Row label="Future" style={{ opacity: 0.92 }}>
          Payout lists · ongoing monitoring
        </Row>
      </div>
      <div style={{ ...rise(1.0, fps, frame), marginTop: 70, fontSize: 26, color: COLORS.textDim, fontFamily: FONT.mono }}>
        future directions — not built today
      </div>
    </Frame>
  );
};

export const EndCard: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const name = rise(0.0, fps, frame);
  const tag = rise(0.35, fps, frame);
  const links = rise(0.6, fps, frame);
  const hack = rise(0.9, fps, frame);
  return (
    <Frame>
      <div style={{ ...name, fontSize: 124, fontWeight: 660, letterSpacing: "-0.02em" }}>
        Where&rsquo;s the Rest?
      </div>
      <div style={{ ...tag, marginTop: 18, fontSize: 40, color: COLORS.blue, fontWeight: 600 }}>
        Follow the payout.
      </div>
      <div style={{ ...links, marginTop: 64, display: "flex", gap: 28, fontSize: 27, fontFamily: FONT.mono, color: COLORS.textDim }}>
        <span style={{ color: COLORS.text }}>payout-reader.up.railway.app</span>
        <span style={{ color: COLORS.border }}>·</span>
        <span style={{ color: COLORS.text }}>github.com/Hesamation/wheres-the-rest</span>
      </div>
      <div style={{ ...hack, marginTop: 58 }}>
        <span style={{
          border: `1.5px solid ${COLORS.border}`, borderRadius: 8, padding: "12px 26px",
          fontSize: 26, letterSpacing: "0.22em", textTransform: "uppercase", color: COLORS.text,
        }}>
          Built at NEAR Hackathon
        </span>
      </div>
      <div style={{ position: "absolute", bottom: 46, fontSize: 20, color: COLORS.textDim, fontFamily: FONT.mono, opacity: interpolate(t, [1.4, 2.0], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }) }}>
        public staging QA case · provider observations · not settlement proof
      </div>
    </Frame>
  );
};
