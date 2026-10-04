// Takes the screenshots REQ-WP-092 requires, from the running build, on LIVE data (no stub): the BTCUSDT 15m chart
// with the Volume pane and then the CVD (base) pane selected, light and dark, at 1280 px and at 390 px, and the
// measurement that the pane's plot area lines up with the chart's.
//
//   PLAYWRIGHT_DIR=<a directory where `npm i playwright` was run> \
//     node specs/136-lower-pane-chart/screenshots.mjs [baseUrl] [outDir]

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

const SIZES = [
  ["desktop", 1280, 1100],
  ["phone", 390, 1500],
];
const PANES = [
  ["volume", "Volume"],
  ["cvd", "CVD (base)"],
];

const browser = await chromium.launch({ executablePath, args: ["--no-sandbox"] });
const report = [];
for (const scheme of ["light", "dark"]) {
  for (const [sizeName, width, height] of SIZES) {
    for (const [slug, label] of PANES) {
      const page = await browser.newPage({ viewport: { width, height }, colorScheme: scheme });
      await page.goto(`${base}/chart/binance/BTCUSDT?tf=15m`, { waitUntil: "networkidle", timeout: 60000 });
      await page.waitForTimeout(2500);
      await page.getByRole("button", { name: label, exact: true }).click();
      await page.waitForTimeout(1200);
      const file = `${out}/pane-${slug}-${scheme}-${sizeName}.png`;
      await page.screenshot({ path: file, fullPage: true });
      // The plot areas: the price axis's left edge on each chart, which is where the plot area ends.
      const edges = await page.evaluate(() => {
        const canvases = [...document.querySelectorAll("canvas")];
        const rects = canvases.map((c) => c.getBoundingClientRect());
        const charts = [...document.querySelectorAll("[data-testid='chart'], [data-testid='pane-chart']")].map((el) => {
          const r = el.getBoundingClientRect();
          return { id: el.getAttribute("data-testid"), left: Math.round(r.left), right: Math.round(r.right), width: Math.round(r.width) };
        });
        return { charts, canvases: rects.length };
      });
      report.push({ file, ...edges });
      console.log(file, JSON.stringify(edges.charts));
      await page.close();
    }
  }
}
await browser.close();
const mismatches = report.filter((r) => {
  const [main, pane] = r.charts;
  return !main || !pane || main.left !== pane.left || main.right !== pane.right;
});
console.log(mismatches.length === 0 ? "plot containers line up in every screenshot" : `MISMATCH in ${mismatches.map((m) => m.file).join(", ")}`);
