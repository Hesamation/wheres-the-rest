import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { BaseStill, ClipWindow, PanZoom, useCamera } from "./Camera";
import { CursorLayer, CursorWaypoint } from "./Cursor";
import { COLORS, FONT } from "./theme";
import type { CamFrames, Scene } from "./types";

const Chip: React.FC<{ text: string; opacity: number; x?: number; y?: number }> = ({ text, opacity, x, y }) => (
  <div
    style={{
      position: "absolute",
      left: x ?? 64,
      ...(y != null ? { top: y } : { bottom: 118 }),
      opacity,
      background: COLORS.charcoal, border: `1px solid ${COLORS.border}`, borderRadius: 8,
      padding: "13px 22px", fontFamily: FONT.mono, fontSize: 26, color: COLORS.text,
      letterSpacing: "0.02em",
    }}
  >
    <span style={{ color: COLORS.blue, marginRight: 14 }}>▪</span>
    {text}
  </div>
);

const EquationOverlay: React.FC<{ progress: number }> = ({ progress }) => {
  const y = (1 - progress) * 40;
  return (
    <div
      style={{
        position: "absolute", left: 0, right: 0, top: 250, opacity: progress,
        display: "flex", justifyContent: "center", transform: `translateY(${y}px)`,
      }}
    >
      <div
        style={{
          background: "rgba(13,15,17,0.94)", border: `1.5px solid ${COLORS.border}`, borderRadius: 14,
          padding: "44px 64px", textAlign: "center", boxShadow: "0 22px 70px rgba(0,0,0,0.5)",
        }}
      >
        <div style={{ fontFamily: FONT.mono, fontSize: 76, color: COLORS.text, letterSpacing: "-0.01em" }}>
          1.000000 <span style={{ color: COLORS.textDim }}>−</span> 0.002400{" "}
          <span style={{ color: COLORS.textDim }}>=</span>{" "}
          <span style={{ color: COLORS.green, fontWeight: 700 }}>0.997600</span>
        </div>
        <div style={{ display: "flex", justifyContent: "center", gap: 66, marginTop: 26, fontSize: 24, color: COLORS.textDim, fontFamily: FONT.mono }}>
          <span>withdrawn on NEAR</span>
          <span style={{ color: COLORS.blue }}>bridge-reported fee</span>
          <span>observed on Base</span>
        </div>
        <div style={{ marginTop: 24, fontSize: 21, color: COLORS.textDim }}>USDC</div>
      </div>
    </div>
  );
};

const QuestionOverlay: React.FC<{ text: string; progress: number }> = ({ text, progress }) => (
  <div
    style={{
      position: "absolute", left: 0, right: 0, top: 360, opacity: progress,
      textAlign: "center", transform: `translateY(${(1 - progress) * 24}px)`,
      fontFamily: FONT.sans, fontSize: 62, fontWeight: 640, color: COLORS.text,
      textShadow: "0 4px 30px rgba(0,0,0,0.8)",
    }}
  >
    {text}
  </div>
);

const ProofCard: React.FC<{ progress: number }> = ({ progress }) => (
  <div
    style={{
      position: "absolute", right: 72, top: 140, width: 780, opacity: progress,
      transform: `translateY(${(1 - progress) * 30}px)`,
      background: "rgba(13,15,17,0.96)", border: `1.5px solid ${COLORS.border}`, borderRadius: 12,
      padding: "30px 36px", boxShadow: "0 22px 70px rgba(0,0,0,0.55)",
      fontFamily: FONT.mono, color: COLORS.text,
    }}
  >
    <div style={{ fontSize: 22, color: COLORS.blue, letterSpacing: "0.16em", textTransform: "uppercase", marginBottom: 18 }}>
      Copy Proof · clipboard contents
    </div>
    <div style={{ fontSize: 24, lineHeight: 1.75 }}>
      <div><span style={{ color: COLORS.textDim }}>Transaction </span>863ZDaRi…1zRe</div>
      <div><span style={{ color: COLORS.textDim }}>Status </span><span style={{ color: COLORS.red }}>MISMATCH</span></div>
      <div style={{ marginTop: 14 }}>
        <span style={{ color: COLORS.textDim }}>Group [0,1,2] </span>0.010000 − 0.002400 ={" "}
        <span style={{ color: COLORS.green }}>0.007600</span> USDC
      </div>
      <div style={{ marginTop: 14 }}><span style={{ color: COLORS.textDim }}>Observed </span>1 · <span style={{ color: COLORS.red }}>unrecorded 2</span></div>
      <div style={{ marginTop: 14, color: COLORS.textDim, fontSize: 21 }}>
        “Amounts are provider observations; ‘proof’ is not a cryptographic proof.”
      </div>
    </div>
  </div>
);

const fadeIn = (t: number, a: number, b: number, dur = 0.25) =>
  interpolate(t, [a, a + dur, b - dur, b], [0, 1, 1, 0], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });

// Edge darkening over the dark app base only; never over white site footage.
const Vignette: React.FC = () => (
  <div
    style={{
      position: "absolute", inset: 0, pointerEvents: "none",
      background:
        "linear-gradient(180deg, rgba(13,15,17,0.30) 0%, rgba(13,15,17,0) 9%, rgba(13,15,17,0) 86%, rgba(13,15,17,0.38) 100%)",
    }}
  />
);

export const ScreenScene: React.FC<{ scene: Scene }> = ({ scene }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;

  // hooks: always called
  const mainCam = useCamera(scene.cam?.frames ?? null);
  const basescanCam = useCamera(scene.basescan?.cam ?? null);
  const bridgeCam = useCamera(scene.bridgeLeg?.cam ?? null);

  const showBasescan = !!scene.basescan && t >= scene.basescan.a && t < scene.basescan.b;
  const showBridge = !!scene.bridgeLeg && t >= scene.bridgeLeg.a && t < scene.bridgeLeg.b;
  const showCopyVideo = !!scene.copyProof && t >= scene.copyProof.a && t < scene.copyProof.a + 1.45;
  const showCopyStill = !!scene.copyProof && t >= scene.copyProof.a + 1.45 && t < scene.copyProof.b;
  const lv = scene.liveVideo;
  const showLiveClick = !!lv && t >= lv.a && t < lv.resultFrom;
  const showLiveResult = !!lv && t >= lv.resultFrom && t < lv.resultFrom + 1.55;
  const showLiveStill = !!lv && t >= lv.resultFrom + 1.55 && t < lv.b;

  return (
    <div style={{ position: "absolute", inset: 0 }}>
      {scene.type === "video" ? (
        <ClipWindow name={scene.base} a={scene.a} b={scene.b} fromSec={scene.play?.from ?? 0} toSec={scene.play?.to} />
      ) : (
        <>
          <PanZoom cam={mainCam}>
            <BaseStill name={scene.base} />
          </PanZoom>
          {!scene.bare && <Vignette />}
        </>
      )}

      {showBasescan && (
        <PanZoom cam={basescanCam}>
          <BaseStill name="basescan" />
        </PanZoom>
      )}
      {showBridge && (
        <PanZoom cam={bridgeCam}>
          <BaseStill name="qa1-evidence-bridge" />
        </PanZoom>
      )}
      {showCopyVideo && (
        <ClipWindow name="copy-proof" a={scene.copyProof.a} b={scene.copyProof.a + 1.45} fromSec={0.15} toSec={1.6} />
      )}
      {showCopyStill && <BaseStill name="qa1-wide" />}
      {showLiveClick && (
        <ClipWindow name="live-query" a={lv.a} b={lv.resultFrom} fromSec={2.25} toSec={3.1} />
      )}
      {showLiveResult && (
        <ClipWindow name="live-query" a={lv.resultFrom} b={lv.resultFrom + 1.55} fromSec={16.3} toSec={17.85} />
      )}
      {showLiveStill && <BaseStill name="live-result" />}

      {scene.equation && <EquationOverlay progress={fadeIn(t, scene.equation.a, scene.equation.b)} />}
      {scene.questionOverlay && (
        <QuestionOverlay text={scene.questionOverlay.text} progress={fadeIn(t, scene.questionOverlay.a, scene.questionOverlay.b)} />
      )}
      {scene.proofCard && (
        <ProofCard
          progress={
            spring({ frame: (t - scene.proofCard.a) * fps, fps, config: { damping: 200 }, durationInFrames: 20 }) *
            interpolate(t, [scene.proofCard.b - 0.2, scene.proofCard.b], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })
          }
        />
      )}
      {(scene.overlays ?? [])
        .filter((o) => !o.skip)
        .map((o) => (
          <Chip key={o.id} text={o.text} opacity={fadeIn(t, o.a, o.b)} x={o.x} y={o.y} />
        ))}

      {scene.cursor && (
        <CursorLayer
          waypoints={scene.cursor as CursorWaypoint[]}
          visibleFrom={scene.cursorWindow?.a ?? scene.a + 0.35}
          visibleTo={scene.cursorWindow?.b ?? scene.b - 0.3}
        />
      )}
    </div>
  );
};
