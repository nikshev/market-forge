// Takes the screenshots REQ-WP-086 requires, from the running build, on LIVE data (no stub): ETHUSDT 1h (whose hourly bars
// had a hole of 148 on 2026-10-04) and BTCUSDT 15m, light and dark, with the Volume pane selected so the markers in the pane
// show too. A later backfill may close those holes, which is why the tests use fixtures and not these.
//
//   PLAYWRIGHT_DIR=<a directory where `npm i playwright` was run> \
//     node specs/137-bar-gaps/screenshots.mjs [baseUrl] [outDir]

import { existsSync, readdirSync } from "node:fs";
import { createRequire } from "node:module";

const dir = process.env.PLAYWRIGHT_DIR;
if (!dir) {
  throw new Error("set PLAYWRIGHT_DIR to a directory where `npm i playwright` was run");
}
const { chromium } = createRequire(`${dir}/package.json`)("playwright");

const base = process.argv[2] ?? "http://127.0.0.1:8081";
const out = process.argv[3] ?? "docs/ui";

const root = `${process.env.HOME}/.cache/ms-playwright`;
let executablePath;
for (const d of readdirSync(root).filter((n) => n.startsWith("chromium-")).sort().reverse()) {
  for (const sub of ["chrome-linux64/chrome", "chrome-linux/chrome"]) {
    if (!executablePath && existsSync(`${root}/${d}/${sub}`)) {
      executablePath = `${root}/${d}/${sub}`;
    }
  }
}

const SHOTS = [
  ["eth1h", "/chart/binance/ETHUSDT?tf=1h"],
  ["btc15m", "/chart/binance/BTCUSDT?tf=15m"],
];

const browser = await chromium.launch({ executablePath, args: ["--no-sandbox"] });
for (const scheme of ["light", "dark"]) {
  for (const [name, path] of SHOTS) {
    const page = await browser.newPage({ viewport: { width: 1280, height: 1250 }, colorScheme: scheme });
    await page.goto(`${base}${path}`, { waitUntil: "networkidle", timeout: 60000 });
    await page.waitForTimeout(2500);
    const notice = await page.getByRole("status", { name: "Gaps in the bars" }).first().innerText().catch(() => "(no notice)");
    const file = `${out}/gaps-${name}-${scheme}.png`;
    await page.screenshot({ path: file, fullPage: true });
    console.log(file, JSON.stringify(notice.split("\n").slice(0, 4)));
    await page.close();
  }
}
await browser.close();
