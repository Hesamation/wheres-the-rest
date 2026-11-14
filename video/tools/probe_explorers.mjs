// Probe both explorer searches for the QA1 source hash. Read-only; screenshots + visible text.
import { chromium } from "playwright";
import { mkdirSync } from "node:fs";
import { resolve } from "node:path";

const VIDEO = resolve(import.meta.dirname, "..");
const RAW = resolve(VIDEO, "raw", "explorer-probe");
mkdirSync(RAW, { recursive: true });

const HASH = "863ZDaRijV6j5RiMXf9GaJDBN86e1j2MNevLQNhR1zRe";
const TARGETS = [
  { name: "near-intents", url: `https://explorer.near-intents.org/?search=${HASH}` },
  { name: "range", url: `https://explorer.range.org/transactions?sc=INTERCHAIN&s=${HASH}` },
];

const browser = await chromium.launch({
  executablePath: process.env.CHROMIUM_PATH ?? "/usr/bin/chromium",
  headless: true,
  args: ["--no-sandbox", "--force-device-scale-factor=1", "--hide-scrollbars", "--mute-audio"],
});

for (const t of TARGETS) {
  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    userAgent: "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/157.0.0.0 Safari/537.36",
    locale: "en-US",
  });
  const page = await context.newPage();
  try {
    await page.goto(t.url, { waitUntil: "domcontentloaded", timeout: 45000 });
    // Give SPAs time to run their search; wait for network to settle
    await page.waitForLoadState("networkidle", { timeout: 30000 }).catch(() => {});
    await page.waitForTimeout(6000);
    const text = (await page.locator("body").innerText().catch(() => "")).slice(0, 3000);
    await page.screenshot({ path: resolve(RAW, `${t.name}.png`) });
    console.log(`\n===== ${t.name} (${new Date().toISOString()}) =====`);
    console.log(text.replace(/\n{2,}/g, "\n").slice(0, 1500));
  } catch (err) {
    console.log(`\n===== ${t.name} ERROR =====`);
    console.log(String(err).slice(0, 500));
    await page.screenshot({ path: resolve(RAW, `${t.name}-error.png`) }).catch(() => {});
  }
  await context.close();
}
await browser.close();
console.log("\nscreenshots in", RAW);
