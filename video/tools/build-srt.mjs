// Builds out/captions.srt from src/manifest.json caption cues.
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const VIDEO = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const manifest = JSON.parse(readFileSync(resolve(VIDEO, "src/manifest.json"), "utf8"));

const fmt = (s) => {
  const ms = Math.round(s * 1000);
  const h = String(Math.floor(ms / 3600000)).padStart(2, "0");
  const m = String(Math.floor((ms % 3600000) / 60000)).padStart(2, "0");
  const sec = String(Math.floor((ms % 60000) / 1000)).padStart(2, "0");
  const mil = String(ms % 1000).padStart(3, "0");
  return `${h}:${m}:${sec},${mil}`;
};

const srt = manifest.captions
  .map((c, i) => `${i + 1}\n${fmt(c.a)} --> ${fmt(c.b)}\n${c.text}\n`)
  .join("\n");

mkdirSync(resolve(VIDEO, "out"), { recursive: true });
writeFileSync(resolve(VIDEO, "out/captions.srt"), srt);
console.log(`captions.srt: ${manifest.captions.length} cues`);
