export type CamFrame = { t: number; s: number; cx: number; cy: number };
export type CamFrames = CamFrame[];

export type Caption = { text: string; a: number; b: number; onCard?: boolean };

export type Overlay = {
  id: string;
  a: number;
  b: number;
  kind: "chip";
  text: string;
  x?: number;
  y?: number;
  skip?: boolean;
};

export type CursorWay = { t: number; x: number; y: number; click?: number };

export type Scene = {
  id: string;
  a: number;
  b: number;
  type: "screen" | "video" | "card";
  base?: string;
  bare?: boolean;
  play?: { from: number; to?: number };
  cam?: { frames: CamFrames } | null;
  overlays?: Overlay[];
  equation?: { a: number; b: number };
  questionOverlay?: { a: number; b: number; text: string };
  basescan?: { a: number; b: number; cam: CamFrames };
  bridgeLeg?: { a: number; b: number; cam: CamFrames };
  copyProof?: { a: number; b: number };
  proofCard?: { a: number; b: number };
  liveVideo?: { a: number; b: number; reconcileAt: number; resultFrom: number };
  cursor?: CursorWay[];
  cursorWindow?: { a: number; b: number };
  card?: "title" | "reveal" | "future" | "end";
};
