// Takes the screenshots REQ-WP-088 requires, from the running build, on LIVE data (no stub): the BTCUSDT 15m chart
// with the "CVD (base)" pane selected, light and dark. The CVD comes from the stored bars, so it has data on the
// live stack from the first worker pass after deployment.
//
//   PLAYWRIGHT_DIR=<a directory where `npm i playwright` was run> \
//     node specs/135-trade-flow-features/screenshots.mjs [baseUrl] [outDir]

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
  const page = await browser.newPage({ viewport: { width: 1280, height: 1000 }, colorScheme: scheme });
  await page.goto(`${base}/chart/binance/BTCUSDT?tf=15m`, { waitUntil: "networkidle", timeout: 60000 });
  await page.waitForTimeout(2500);
  // Volume is first and selected; choose the CVD pane.
  await page.getByRole("button", { name: "CVD (base)" }).click();
  await page.waitForTimeout(800);
  const file = `${out}/cvd-pane-${scheme}.png`;
  await page.screenshot({ path: file, fullPage: true });
  console.log(file);
  await page.close();
}
await browser.close();
