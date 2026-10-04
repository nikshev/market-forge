// Takes the screenshots REQ-WP-083 requires, from the running build, and measures the page width.
//
//   PLAYWRIGHT_DIR=<a directory where `npm i playwright` was run> \
//     node specs/132-material-ui/screenshots.mjs [baseUrl] [outDir]
//
// Playwright is not a dependency of this project, on purpose: it is a tool for looking, installed where it
// is used. Chromium is taken from playwright's own cache.
//
// Eight screenshots: the overview and a chart, light and dark, at 1280 px and 390 px. And for each of the
// two pages at 390 px, `scrollWidth <= innerWidth`: no horizontal page scroll.

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

const PAGES = [
  ["overview", "/"],
  ["chart", "/chart/binance/BTCUSDT?tf=15m"],
];
const SIZES = [
  ["desktop", 1280, 860],
  ["phone", 390, 844],
];

const browser = await chromium.launch({ executablePath, args: ["--no-sandbox"] });
const widths = [];
for (const [name, path] of PAGES) {
  for (const scheme of ["light", "dark"]) {
    for (const [label, width, height] of SIZES) {
      const page = await browser.newPage({ viewport: { width, height }, colorScheme: scheme });
      await page.goto(`${base}${path}`, { waitUntil: "networkidle", timeout: 60000 });
      await page.waitForTimeout(2500);
      const file = `${out}/${name}-${scheme}-${label}.png`;
      await page.screenshot({ path: file, fullPage: label === "phone" });
      const m = await page.evaluate(() => ({
        scrollWidth: document.documentElement.scrollWidth,
        innerWidth: window.innerWidth,
      }));
      if (label === "phone") {
        widths.push({ page: name, scheme, ...m, ok: m.scrollWidth <= m.innerWidth });
      }
      console.log(`${file}  scrollWidth=${m.scrollWidth} innerWidth=${m.innerWidth}`);
      await page.close();
    }
  }
}
await browser.close();
console.log(JSON.stringify(widths));
