// Takes the screenshots REQ-WP-089 requires, from the running build, on LIVE data (no stub): BTCUSDT 15m with the profile at
// the side of the chart, light and dark, in the 24h window and the 4h window. Collection began on 2026-10-04, so the coverage
// line says how little the profile covers; that is the point of the line.
//
//   PLAYWRIGHT_DIR=<a directory where `npm i playwright` was run> \
//     node specs/138-volume-profile/screenshots.mjs [baseUrl] [outDir]

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

const browser = await chromium.launch({ executablePath, args: ["--no-sandbox"] });
for (const scheme of ["light", "dark"]) {
  for (const window of ["24h", "4h"]) {
    const page = await browser.newPage({ viewport: { width: 1280, height: 1100 }, colorScheme: scheme });
    await page.goto(`${base}/chart/binance/BTCUSDT?tf=15m`, { waitUntil: "networkidle", timeout: 60000 });
    await page.waitForTimeout(2000);
    if (window !== "24h") {
      await page.getByRole("group", { name: "Profile window" }).getByRole("button", { name: `${window} profile`, exact: true }).click();
      await page.waitForTimeout(2000);
    }
    const status = await page.getByRole("status", { name: "Volume profile" }).innerText().catch(() => "(no status)");
    const file = `${out}/profile-btc15m-${window}-${scheme}.png`;
    await page.screenshot({ path: file, fullPage: true });
    console.log(file, JSON.stringify(status));
    await page.close();
  }
}
await browser.close();
