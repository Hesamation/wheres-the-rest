// Smoke capture: prove Playwright + system Chromium can record genuine 1920x1080 app footage.
// Saves a short webm of the QA1 deep link loading and the finding expanding, plus stills.
import { chromium } from "playwright";
import { mkdirSync } from "node:fs";
import { resolve } from "node:path";

const VIDEO = resolve(import.meta.dirname, "..");
const RAW = resolve(VIDEO, "raw", "smoke");
mkdirSync(RAW, { recursive: true });

const APP = process.env.APP_URL ?? "http://127.0.0.1:8765";

const browser = await chromium.launch({
  executablePath: process.env.CHROMIUM_PATH ?? "/usr/bin/chromium",
  headless: true,
  args: ["--no-sandbox", "--force-device-scale-factor=1", "--hide-scrollbars", "--mute-audio"],
});
const context = await browser.newContext({
  viewport: { width: 1920, height: 1080 },
  recordVideo: { dir: RAW, size: { width: 1920, height: 1080 } },
});
const page = await context.newPage();

await page.goto(`${APP}/?example=qa1`, { waitUntil: "networkidle" });
await page.waitForTimeout(1200); // let the saved report render fully
await page.screenshot({ path: resolve(RAW, "qa1-workbench.png") });

// Expand the grouped finding if collapsed (genuine interaction, rehearsed for the edit)
const finding = page.locator("button, [role=button], .finding-row, .row").filter({ hasText: /GROUP|deficit|0\.010000/i }).first();
if (await finding.count()) {
  await finding.click().catch(() => {});
  await page.waitForTimeout(800);
}
await page.screenshot({ path: resolve(RAW, "qa1-expanded.png") });
await page.waitForTimeout(2500); // some recorded footage

await context.close();
const videoPath = await page.video()?.path().catch(() => null);
await browser.close();
console.log("smoke capture done:", videoPath ?? "(no video path)");
