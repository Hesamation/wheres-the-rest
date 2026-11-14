// Builds src/manifest.json: the editable scene/caption/overlay table for the film.
// All timings are anchored to word timestamps in assets/narration-timing.json,
// so re-transcribing a new narration recording re-syncs the edit on rebuild.
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const VIDEO = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const timing = JSON.parse(readFileSync(resolve(VIDEO, "assets/narration-timing.json"), "utf8"));

// word("Where's", 11) -> start of first word matching text in segment 11
const word = (text, seg) => {
  const s = timing.segments[seg];
  const w = s.words.find((w) => w.w.replace(/[^a-zA-Z0-9']/g, "").toLowerCase() === text.toLowerCase());
  if (!w) throw new Error(`anchor not found: ${text} in segment ${seg}`);
  return w;
};
const t0 = (text, seg) => word(text, seg).start;
const t1 = (text, seg) => word(text, seg).end;
const NARR_END = 101.78; // last word ends ("payout." S30)
const FPS = 30;
const HOLD_END = 105.0; // brief end hold after narration

// ---- caption cues (script text; start/end anchored to spoken words) ----
const captions = [
  { text: "Executed.", a: t0("Executed", 0), b: 1.55 },
  { text: "Great. Now show me what arrived.", a: t0("Great", 0), b: t1("arrived", 0) + 0.3 },
  { text: "Start simple.", a: t0("Start", 1), b: t1("simple", 1) + 0.25 },
  { text: "One USDC withdrawn on NEAR.", a: t0("One", 2), b: t1("near", 2) + 0.25 },
  { text: "A bridge-reported fee.", a: t0("A", 3), b: t1("fee", 3) + 0.25 },
  { text: "0.9976 USDC observed on Base.", a: t0("0", 4), b: t1("base", 4) + 0.3 },
  { text: "The amounts line up.", a: t0("The", 5), b: t1("up", 5) + 0.3 },
  { text: "Now try three withdrawals.", a: t0("Now", 6), b: t1("withdrawals", 6) + 0.3 },
  { text: "In this public staging QA test on mainnet:", a: t0("In", 7), b: t1("mainnet", 7) + 0.3 },
  { text: "Three identical burns. Same recipient.", a: t0("three", 8), b: t1("recipient", 9) + 0.25 },
  { text: "One observed transfer.", a: t0("One", 10), b: t1("transfer", 10) + 0.3, onCard: true },
  { text: "Cross-chain explorers already exist.", a: t0("Cross", 11), b: t1("exist", 11) + 0.25 },
  { text: "We checked this source hash in NEAR Intents Explorer and Range.", a: t0("so", 11), b: t1("range", 12) + 0.25 },
  { text: "Neither search returned a result for this hash.", a: t0("Neither", 12), b: t1("hash", 13) + 0.25 },
  { text: "Our payout question remains:", a: t0("Our", 13), b: t1("remains", 13) + 0.25 },
  { text: "Do all three withdrawals have matching evidence?", a: t0("Do", 13), b: t1("evidence", 14) + 0.3 },
  { text: "Where's the Rest? checks the source burns, bridge records and Base transfers in one read-only report.", a: t0("Where's", 14), b: t1("report", 15) + 0.25 },
  { text: "Two burns have no matching bridge records in this saved capture.", a: t0("Two", 15), b: t1("capture", 16) + 0.25 },
  { text: "The evidence can't identify which identical burn matched, so the report keeps them grouped.", a: t0("The", 16), b: t1("grouped", 17) + 0.25 },
  { text: "One observed transfer gets counted once. The unknowns stay visible.", a: t0("One", 17), b: t1("visible", 17) + 0.3 },
  { text: "Open the finding. Follow the receipt. Check the amounts.", a: t0("Open", 18), b: t1("amounts", 18) + 0.25 },
  { text: "The bridge reports the link and fee.", a: t0("The", 18), b: t1("fee", 19) + 0.25 },
  { text: "These are provider observations, not settlement proof.", a: t0("These", 19), b: t1("proof", 19) + 0.3 },
  { text: "Then share the report, with the evidence attached.", a: t0("Then", 19), b: t1("attached", 20) + 0.25 },
  { text: "Replay a dated capture, or query the providers again.", a: t0("Replay", 21), b: t1("again", 22) + 0.3 },
  { text: "Missing records don't prove permanent loss.", a: t0("Missing", 23), b: t1("loss", 24) + 0.4 },
  { text: "Today: one public NEAR-to-Base USDC route.", a: t0("Today", 24), b: t1("route", 26) + 0.3 },
  { text: "Payout lists and ongoing monitoring are future work.", a: t0("Payout", 27), b: t1("work", 28) + 0.35 },
  { text: "Where's the Rest? Follow the payout.", a: t0("Where's", 29), b: t1("payout", 30) + 0.4, onCard: true },
];

// ---- camera helper: keyframes {t, s, cx, cy} in layout px (1920x1080 space) ----
const cam = (frames) => ({ frames });

// ---- scenes ----
const scenes = [
  {
    id: "title", a: 0.0, b: 1.55, type: "card", card: "title",
  },
  {
    id: "workbench-intro", a: 1.55, b: 4.55, type: "screen", base: "control-wide",
    cam: cam([{ t: 1.55, s: 1.0, cx: 960, cy: 540 }]),
  },
  {
    id: "control-walkthrough", a: 4.55, b: 17.1, type: "screen", base: "control-row",
    cam: cam([
      { t: 4.55, s: 1.0, cx: 960, cy: 540 },
      { t: 6.9, s: 1.5, cx: 1100, cy: 505 },
      { t: 8.94, s: 1.5, cx: 1100, cy: 505 },
      { t: 9.6, s: 2.3, cx: 1060, cy: 505 },
      { t: 10.92, s: 2.3, cx: 1060, cy: 505 },
      { t: 11.7, s: 2.3, cx: 1225, cy: 505 },
      { t: 12.9, s: 2.3, cx: 1225, cy: 505 },
      { t: 13.6, s: 1.55, cx: 1180, cy: 440 },
      { t: 15.48, s: 1.55, cx: 1180, cy: 440 },
      { t: 16.1, s: 1.0, cx: 960, cy: 540 },
    ]),
    overlays: [
      { id: "fee-tag", a: 8.94, b: 10.7, kind: "chip", text: "bridge-reported fee", x: 90, y: 900 },
    ],
    equation: { a: 15.3, b: 17.05 },
  },
  {
    id: "qa1-select", a: 17.1, b: 20.4, type: "video", base: "qa1-click",
    // video timeline: 0-1.0s control idle, ~1.0s loading bar, ~3.0s QA1 content.
    // play.from=0.5 -> loading lands film 17.6, content lands film 19.6.
    play: { from: 0.5 },
    cursor: [
      { t: 17.3, x: 820, y: 380 },
      { t: 17.5, x: 1146, y: 123, click: 17.6 },
    ],
  },
  {
    id: "qa1-reveal", a: 20.4, b: 29.2, type: "screen", base: "qa1-kpis",
    cam: cam([
      { t: 20.4, s: 1.0, cx: 960, cy: 540 },
      { t: 23.56, s: 1.0, cx: 960, cy: 540 },
      { t: 24.25, s: 2.05, cx: 487, cy: 340 },
      { t: 25.84, s: 2.05, cx: 487, cy: 340 },
      { t: 26.45, s: 2.3, cx: 700, cy: 500 },
      { t: 27.46, s: 2.3, cx: 700, cy: 500 },
      { t: 28.1, s: 2.05, cx: 1117, cy: 340 },
    ]),
    overlays: [
      { id: "qa-context", a: 19.9, b: 23.4, kind: "chip", text: "public staging QA test · mainnet · saved evidence 2026-11-10", x: 90, y: 900 },
    ],
  },
  {
    id: "question-card", a: 29.2, b: 31.58, type: "card", card: "reveal",
  },
  {
    id: "explorer-ni", a: 31.58, b: 37.9, type: "screen", base: "explorer-ni", bare: true,
    cam: cam([
      { t: 31.58, s: 1.0, cx: 960, cy: 540 },
      { t: 34.0, s: 1.5, cx: 960, cy: 700 },
      { t: 36.2, s: 1.15, cx: 960, cy: 700 },
    ]),
    overlays: [
      { id: "search-label", a: 31.7, b: 37.9, kind: "chip", text: "public source-hash searches · 2026-11-14 · limited lookup, not a product comparison", x: 64, y: 52 },
    ],
  },
  {
    id: "explorer-range", a: 37.9, b: 44.2, type: "screen", base: "explorer-range", bare: true,
    cam: cam([
      { t: 37.9, s: 1.0, cx: 960, cy: 540 },
      { t: 39.3, s: 1.12, cx: 960, cy: 400 },
      { t: 41.3, s: 1.0, cx: 960, cy: 540 },
    ]),
    overlays: [
      { id: "search-label-2", a: 37.9, b: 44.2, kind: "chip", text: "public source-hash searches · 2026-11-14 · limited lookup, not a product comparison", x: 64, y: 52 },
    ],
  },
  {
    id: "payout-question", a: 44.2, b: 47.5, type: "screen", base: "qa1-wide",
    cam: cam([{ t: 44.2, s: 1.0, cx: 960, cy: 540 }]),
    questionOverlay: { a: 44.4, b: 47.4, text: "Do all three withdrawals have matching evidence?" },
  },
  {
    id: "three-legs", a: 47.5, b: 69.7, type: "screen", base: "qa1-wide",
    cam: cam([
      { t: 47.5, s: 1.0, cx: 960, cy: 540 },
      { t: 48.24, s: 1.0, cx: 960, cy: 540 },
      { t: 49.0, s: 2.2, cx: 551, cy: 715 },
      { t: 50.14, s: 2.2, cx: 551, cy: 715 },
      { t: 50.9, s: 2.2, cx: 960, cy: 715 },
      { t: 51.18, s: 2.2, cx: 960, cy: 715 },
      { t: 51.95, s: 2.2, cx: 1368, cy: 725 },
      { t: 54.54, s: 2.2, cx: 1368, cy: 725 },
      { t: 55.3, s: 1.3, cx: 960, cy: 640 },
      { t: 58.68, s: 1.3, cx: 960, cy: 640 },
      { t: 59.45, s: 2.7, cx: 551, cy: 725 },
      { t: 63.08, s: 2.7, cx: 551, cy: 725 },
      { t: 63.75, s: 1.28, cx: 960, cy: 505 },
    ]),
    overlays: [
      { id: "leg-near", a: 48.3, b: 50.0, kind: "chip", text: "NEAR RPC observation", x: 90, y: 900 },
      { id: "leg-bridge", a: 50.2, b: 51.95, kind: "chip", text: "bridge-reported link + fee", x: 90, y: 900 },
      { id: "leg-base", a: 52.1, b: 54.4, kind: "chip", text: "Base RPC observation", x: 90, y: 900 },
    ],
  },
  {
    id: "receipt-and-share", a: 69.7, b: 83.9, type: "screen", base: "qa1-evidence-dest",
    cam: cam([
      { t: 69.7, s: 2.1, cx: 1368, cy: 725 },
      { t: 71.5, s: 1.05, cx: 960, cy: 540 },
    ]),
    basescan: { a: 71.5, b: 75.4, cam: [{ t: 71.5, s: 1.0, cx: 960, cy: 540 }, { t: 72.2, s: 1.8, cx: 960, cy: 430 }, { t: 75.0, s: 1.8, cx: 960, cy: 430 }] },
    bridgeLeg: { a: 75.4, b: 79.3, cam: [{ t: 75.4, s: 2.2, cx: 960, cy: 715 }] },
    copyProof: { a: 79.3, b: 83.9 },
    overlays: [
      { id: "provider-tag", a: 74.96, b: 79.3, kind: "chip", text: "provider observations · not settlement proof", x: 90, y: 900 },
      { id: "live-tag-2", a: 87.8, b: 91.4, kind: "chip", text: "", x: 0, y: 0, skip: true },
    ],
    proofCard: { a: 80.75, b: 83.8 },
    cursor: [
      { t: 79.5, x: 980, y: 520 },
      { t: 80.0, x: 1203, y: 24, click: 80.15 },
    ],
    cursorWindow: { a: 79.3, b: 81.0 },
  },
  {
    id: "saved-and-live", a: 83.9, b: 91.5, type: "screen", base: "live-prefill",
    cam: cam([{ t: 83.9, s: 1.0, cx: 960, cy: 540 }]),
    liveVideo: { a: 87.1, b: 91.5, reconcileAt: 87.35, resultFrom: 87.95 },
    overlays: [
      { id: "live-tag", a: 87.9, b: 91.45, kind: "chip", text: "fresh live query · 2026-11-14", x: 90, y: 900 },
    ],
  },
  {
    id: "today-future", a: 91.5, b: 99.3, type: "card", card: "future",
  },
  {
    id: "end-card", a: 99.3, b: HOLD_END, type: "card", card: "end",
  },
];

const manifest = {
  fps: FPS,
  width: 1920,
  height: 1080,
  durationSec: HOLD_END,
  durationInFrames: Math.round(HOLD_END * FPS),
  narration: { file: "narration-normalized.wav", durationSec: NARR_END },
  captions,
  scenes,
};

mkdirSync(resolve(VIDEO, "src"), { recursive: true });
writeFileSync(resolve(VIDEO, "src/manifest.json"), JSON.stringify(manifest, null, 2));
console.log(
  `manifest: ${scenes.length} scenes, ${captions.length} captions, ${manifest.durationInFrames} frames (${HOLD_END}s)`,
);
