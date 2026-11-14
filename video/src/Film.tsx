import React from "react";
import { AbsoluteFill, Audio, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import manifest from "./manifest.json";
import { ScreenScene } from "./ScreenScene";
import { CaptionBar } from "./Captions";
import { TitleCard, RevealCard, FutureCard, EndCard } from "./Cards";
import type { Scene } from "./types";

const CARDS = { title: TitleCard, reveal: RevealCard, future: FutureCard, end: EndCard };

export const Film: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const scenes = manifest.scenes as Scene[];

  return (
    <AbsoluteFill style={{ background: "#0d0f11", fontFamily: "'IBM Plex Sans', sans-serif" }}>
      <Audio src={staticFile(manifest.narration.file)} />

      {scenes.map((scene) => {
        if (t < scene.a || t > scene.b) return null;
        // scene-level crossfade
        const fade = Math.min(
          Math.min(1, (t - scene.a) / 0.28 + 0.001),
          Math.min(1, (scene.b - t) / 0.28 + 0.001),
        );
        if (scene.type === "card" && scene.card) {
          const Card = CARDS[scene.card];
          return (
            <AbsoluteFill key={scene.id} style={{ opacity: scene.id === "title" || scene.id === "end-card" ? fade : fade * 0.98 }}>
              <Card />
            </AbsoluteFill>
          );
        }
        return (
          <AbsoluteFill key={scene.id} style={{ opacity: fade }}>
            <ScreenScene scene={scene} />
          </AbsoluteFill>
        );
      })}

      <CaptionBar captions={manifest.captions as import("./types").Caption[]} />
    </AbsoluteFill>
  );
};
