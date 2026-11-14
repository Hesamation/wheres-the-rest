// Master footage capture: genuine app + explorer interactions at 1920x1080@30.
// Each clip records a click log (for the Remotion cursor overlay) and metadata.
// Usage: node tools/capture_footage.mjs [app|explorers|live]
import { chromium } from "playwright";
import { mkdirSync, writeFileSync, existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";

const VIDEO = resolve(import.meta.dirname, "..");
const RAW = resolve(VIDEO, "raw", "footage");
const STILLS = resolve(VIDEO, "raw", "stills");
mkdirSync(RAW, { recursive: true });
mkdirSync(STILLS, { recursive: true });

const APP = process.env.APP_URL ?? "http://127.0.0.1:8765";
const QA1_HASH = "863ZDaRijV6j5RiMXf9GaJDBN86e1j2MNevLQNhR1zRe";
const QA1_BASE_TX = "https://basescan.org/tx/0xcc876a99edda48c8a3d754bc3237438de0b903ad6967aebe41bbc7b624261e6e";
const UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/157.0.0.0 Safari/537.36";

const INDEX = resolve(RAW, "index.json");
const index = existsSync(INDEX) ? JSON.parse(readFileSync(INDEX, "utf8")) : { clips: {}, stills: {}, notes: {} };

const browser = await chromium.launch({
  executablePath: process.env.CHROMIUM_PATH ?? "/usr/bin/chromium",
  headless: true,
  args: ["--no-sandbox", "--force-device-scale-factor=1", "--hide-scrollbars", "--mute-audio", "--autoplay-policy=no-user-gesture-required"],
});

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function newRecordingCtx() {
  const ctx = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    recordVideo: { dir: RAW, size: { width: 1920, height: 1080 } },
    userAgent: UA,
    locale: "en-US",
    permissions: ["clipboard-read", "clipboard-write"],
  });
  await ctx.grantPermissions(["clipboard-read", "clipboard-write"]);
  return ctx;
}

// Run one scripted clip. steps receive helpers; click() logs cursor position+time.
async function clip(name, { url, gotoOpts, run, settle = 0 }) {
  const ctx = await newRecordingCtx();
  const page = await ctx.newPage();
  const t0 = Date.now();
  const clicks = [];
  const log = { name, startedAt: new Date().toISOString(), url, clicks: [] };

  const center = async (locator) => {
    const bb = await locator.boundingBox();
    if (!bb) throw new Error(`no bounding box for ${name}`);
    return { x: bb.x + bb.width / 2, y: bb.y + bb.height / 2 };
  };
  const click = async (locator, label) => {
    const pos = await center(locator);
    clicks.push({ t: (Date.now() - t0) / 1000, ...pos, label: label ?? "click" });
    await page.mouse.move(pos.x, pos.y, { steps: 12 });
    await sleep(120);
    await page.mouse.down(); await sleep(60); await page.mouse.up();
  };
  const note = (k, v) => { log[k] = v; };

  try {
    if (url) {
      await page.goto(url, gotoOpts ?? { waitUntil: "domcontentloaded" });
      await page.waitForLoadState("networkidle", { timeout: 30000 }).catch(() => {});
    }
    if (settle) await sleep(settle);
    await run({ page, click, center, sleep, note });
    await sleep(1.0); // tail padding so recording doesn't cut the last frame
    await ctx.close();
    const file = await page.video().path();
    log.file = file;
    log.clicks = clicks;
    index.clips[name] = log;
    writeFileSync(INDEX, JSON.stringify(index, null, 2));
    console.log(`OK  ${name}  clicks=${clicks.length}`);
  } catch (err) {
    console.log(`ERR ${name}: ${String(err).slice(0, 300)}`);
    await ctx.close().catch(() => {});
  }
}

async function still(name, { url, dsf = 2, run }) {
  const ctx = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    deviceScaleFactor: dsf,
    userAgent: UA,
    locale: "en-US",
  });
  const page = await ctx.newPage();
  try {
    if (url) {
      await page.goto(url, { waitUntil: "domcontentloaded" });
      await page.waitForLoadState("networkidle", { timeout: 30000 }).catch(() => {});
    }
    await sleep(1500);
    if (run) await run({ page, sleep });
    const file = resolve(STILLS, `${name}.png`);
    await page.screenshot({ path: file });
    index.stills[name] = { file, dsf };
    writeFileSync(INDEX, JSON.stringify(index, null, 2));
    console.log(`OK  still ${name}`);
  } catch (err) {
    console.log(`ERR still ${name}: ${String(err).slice(0, 300)}`);
  }
  await ctx.close();
}

const WHICH = process.argv[2] ?? "all";
const want = (g) => WHICH === "all" || WHICH === g;

// ---------- App footage ----------
if (want("app")) {
  const workbenchReady = async (page) => {
    await page.waitForSelector("#findings-tbody tr", { timeout: 20000 });
    await sleep(1600); // render + fade-in settle
  };

  await clip("control-loaded", {
    url: `${APP}/?example=prod_control`, settle: 0,
    run: async ({ page }) => { await workbenchReady(page); await sleep(5.5); },
  });

  await clip("control-expand", {
    url: `${APP}/?example=prod_control`,
    run: async ({ page, sleep }) => {
      await workbenchReady(page);
      await sleep(1.2); // first row auto-expands on load; no toggle click (it would collapse)
      // slow drift from the findings table down to the evidence trail cards
      for (let i = 0; i < 12; i++) { await page.mouse.wheel(0, 55); await sleep(270); }
      await sleep(2.2);
    },
  });

  await clip("qa1-click", {
    url: `${APP}/?example=prod_control`,
    run: async ({ page, click, sleep }) => {
      await workbenchReady(page);
      await sleep(1.2);
      await click(page.locator("#example-pills-container [role=radio]", { hasText: "QA1" }).first(), "select QA1");
      await page.waitForFunction(
        () => document.querySelector("#kpi-unrecorded-count")?.textContent === "2",
        { timeout: 20000 },
      ).catch(() => {});
      await sleep(4.5);
    },
  });

  await clip("qa1-reveal", {
    url: `${APP}/?example=qa1`,
    run: async ({ page, sleep }) => { await workbenchReady(page); await sleep(6.0); },
  });

  await clip("qa1-expand", {
    url: `${APP}/?example=qa1`,
    run: async ({ page, sleep }) => {
      await workbenchReady(page);
      await sleep(1.0); // group finding auto-expanded on load; toggle would collapse it
      // drift through group alert + trail cards (source/bridge/destination legs)
      for (let i = 0; i < 9; i++) { await page.mouse.wheel(0, 65); await sleep(250); }
      await sleep(1.0);
      for (let i = 0; i < 9; i++) { await page.mouse.wheel(0, 65); await sleep(250); }
      await sleep(2.2);
    },
  });

  await clip("copy-proof", {
    url: `${APP}/?example=qa1`,
    run: async ({ page, click, sleep, note }) => {
      await workbenchReady(page);
      await sleep(0.8);
      await click(page.locator("#btn-copy-proof"), "Copy Proof");
      await sleep(2.6);
      const text = await page.evaluate(() => navigator.clipboard.readText().catch(() => ""));
      note("clipboardChars", text.length);
      writeFileSync(resolve(RAW, "copy-proof-contents.txt"), text);
      await sleep(0.5);
    },
  });

  // High-res stills for zoom beats (crisp at 1.3-1.5x crops)
  await still("control-wide", { url: `${APP}/?example=prod_control` });
  await still("control-row", {
    url: `${APP}/?example=prod_control`,
    run: async ({ page }) => {
      await page.waitForSelector("#findings-tbody tr", { timeout: 20000 });
      await sleep(1600);
      await page.locator("#findings-table").scrollIntoViewIfNeeded();
      await sleep(400);
    },
  });
  await still("control-evidence", {
    url: `${APP}/?example=prod_control`,
    run: async ({ page, sleep }) => {
      await page.waitForSelector(".trail-grid .trail-card", { timeout: 20000 });
      await sleep(1600);
      await page.locator(".trail-grid").first().scrollIntoViewIfNeeded();
      await sleep(400);
    },
  });
  await still("qa1-wide", { url: `${APP}/?example=qa1` });
  await still("qa1-kpis", {
    url: `${APP}/?example=qa1`,
    run: async ({ page, sleep }) => {
      await page.waitForSelector("#findings-tbody tr", { timeout: 20000 });
      await sleep(1600);
      await page.locator(".kpi-grid").scrollIntoViewIfNeeded();
      await sleep(400);
    },
  });
  await still("qa1-evidence-bridge", {
    url: `${APP}/?example=qa1`,
    run: async ({ page, sleep }) => {
      await page.waitForSelector(".trail-grid .trail-card", { timeout: 20000 });
      await sleep(1600);
      await page.locator(".trail-card").nth(1).scrollIntoViewIfNeeded();
      await sleep(400);
    },
  });
  await still("qa1-evidence-dest", {
    url: `${APP}/?example=qa1`,
    run: async ({ page, sleep }) => {
      await page.waitForSelector(".trail-grid .trail-card", { timeout: 20000 });
      await sleep(1600);
      await page.locator(".trail-card").nth(2).scrollIntoViewIfNeeded();
      await sleep(400);
    },
  });
  await still("live-prefill", {
    url: `${APP}/?example=qa1`,
    run: async ({ page, sleep }) => {
      await page.waitForSelector("#findings-tbody tr", { timeout: 20000 });
      await sleep(1600);
      await page.locator("#tab-live").click();
      await sleep(1200);
    },
  });
}

// ---------- Explorer + receipt footage ----------
if (want("explorers")) {
  await clip("explorer-ni", {
    url: `https://explorer.near-intents.org/?search=${QA1_HASH}`,
    gotoOpts: { waitUntil: "domcontentloaded", timeout: 45000 },
    run: async ({ page, sleep }) => {
      await sleep(6500);
      await page.locator("text=No results").first().scrollIntoViewIfNeeded({ timeout: 10000 }).catch(() => {});
      await page.evaluate(() => window.scrollBy(0, -140));
      await sleep(5.0);
    },
  });
  await clip("explorer-range", {
    url: `https://explorer.range.org/transactions?sc=INTERCHAIN&s=${QA1_HASH}`,
    gotoOpts: { waitUntil: "domcontentloaded", timeout: 45000 },
    run: async ({ page, sleep }) => {
      await sleep(7000);
      await page.locator("text=No results found").first().scrollIntoViewIfNeeded({ timeout: 10000 }).catch(() => {});
      await page.evaluate(() => window.scrollBy(0, -80));
      await sleep(5.0);
    },
  });
  await clip("basescan-qa1", {
    url: QA1_BASE_TX,
    gotoOpts: { waitUntil: "domcontentloaded", timeout: 45000 },
    run: async ({ page, sleep }) => {
      await sleep(7000);
      await page.locator("#content").scrollIntoViewIfNeeded().catch(() => {});
      await sleep(4.5);
    },
  });
}

// ---------- Live query (genuine; may fail) ----------
if (want("live")) {
  await clip("live-query", {
    url: `${APP}/?example=prod_control`,
    run: async ({ page, click, sleep, note }) => {
      await page.waitForSelector("#findings-tbody tr", { timeout: 20000 });
      await sleep(1600);
      await click(page.locator("#tab-live"), "Live Query tab");
      await sleep(2.2);
      await click(page.locator("#btn-submit-live"), "Reconcile");
      const tStart = Date.now();
      // genuine completion: loading bar shows, then hides, then provenance chip flips to Live
      await page.waitForFunction(
        () => document.getElementById("loading-state")?.style.display === "flex",
        { timeout: 8000, polling: 100 },
      ).catch(() => note("loadingBarSeen", false));
      await page.waitForFunction(
        () => document.getElementById("loading-state")?.style.display === "none",
        { timeout: 125000, polling: 250 },
      ).catch(() => note("loadingBarHiddenTimeout", true));
      await sleep(1200);
      const chip = await page.locator("#provenance-chip-text").innerText().catch(() => "?");
      const title = await page.locator("#outcome-title").innerText().catch(() => "?");
      const observed = await page.locator("#kpi-observed-count").innerText().catch(() => "?");
      const modeBadge = await page.locator("#outcome-mode-badge").innerText().catch(() => "?");
      note("chip", chip);
      note("result", `${title} / observed=${observed} / badge=${modeBadge}`);
      note("elapsedSec", (Date.now() - tStart) / 1000);
      await sleep(4.5);
    },
  });
}

await browser.close();
writeFileSync(INDEX, JSON.stringify(index, null, 2));
console.log("index:", INDEX);
