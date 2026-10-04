// Takes the screenshots REQ-WP-084 requires, from the running build.
//
//   PLAYWRIGHT_DIR=<a directory where `npm i playwright` was run> \
//     node specs/133-chart-candidates-no-data/screenshots.mjs [baseUrl] [outDir]
//
// Eight images, light and dark, desktop width:
//   chart-candidates-off / chart-candidates-on   the chart as opened, and with the switch pressed (live data)
//   chart-panes-live-no-data                     the pane row on the live stack: the features table has no
//                                                producer yet, so every pane reads "no data" -- this is real
//   chart-panes-some-data                        the same row with the features series STUBBED to carry `cvd`
//                                                and `ofi_1m` (playwright answers the request itself): a
//                                                picture of what a populated row looks like, not live data
//
// Playwright is not a dependency of this project, on purpose; Chromium is taken from playwright's own cache.

import { existsSync, readdirSync } from "node:fs";
import { createRequire } from "node:module";

const dir = process.env.PLAYWRIGHT_DIR;
if (!dir) {
  throw new Error("set PLAYWRIGHT_DIR to a directory where `npm i playwright` was run");
}
const { chromium } = createRequire(`${dir}/package.json`)("playwright");

const base = process.argv[2] ?? "http://127.0.0.1:8081";
const out = process.argv[3] ?? "docs/ui";
const PATH = "/chart/binance/BTCUSDT?tf=15m";

const root = `${process.env.HOME}/.cache/ms-playwright`;
let executablePath;
for (const d of readdirSync(root).filter((n) => n.startsWith("chromium-")).sort().reverse()) {
  for (const sub of ["chrome-linux64/chrome", "chrome-linux/chrome"]) {
    if (!executablePath && existsSync(`${root}/${d}/${sub}`)) {
      executablePath = `${root}/${d}/${sub}`;
    }
  }
}

// A features series over the requested range: `cvd` and `ofi_1m` only, 60 points. Times are the wire's
// strings; the values are a smooth shape, enough to see a line.
function stubbedSeries(url) {
  const params = new URL(url).searchParams;
  const start = BigInt(params.get("start_ns"));
  const end = BigInt(params.get("end_ns"));
  const points = [];
  for (let i = 0; i < 60; i += 1) {
    const at = start + ((end - start) * BigInt(i)) / 59n;
    points.push({
      at_ns: at.toString(),
      values: { cvd: Math.sin(i / 7) * 40 + i, ofi_1m: Math.cos(i / 5) * 12 },
    });
  }
  return { points };
}

const browser = await chromium.launch({ executablePath, args: ["--no-sandbox"] });

async function shoot(scheme, name, { stub = false, press = false, section = null }) {
  const page = await browser.newPage({ viewport: { width: 1280, height: 1000 }, colorScheme: scheme });
  if (stub) {
    await page.route("**/api/v1/features/timeseries*", (route) =>
      route.fulfill({ contentType: "application/json", body: JSON.stringify(stubbedSeries(route.request().url())) }),
    );
  }
  await page.goto(`${base}${PATH}`, { waitUntil: "networkidle", timeout: 60000 });
  await page.waitForTimeout(2500);
  if (press) {
    await page.getByRole("button", { name: "Candidate extrema" }).click();
    await page.waitForTimeout(800);
  }
  const file = `${out}/${name}-${scheme}.png`;
  if (section) {
    await page.getByLabel(section).first().screenshot({ path: file });
  } else {
    await page.screenshot({ path: file });
  }
  console.log(file);
  await page.close();
}

for (const scheme of ["light", "dark"]) {
  await shoot(scheme, "chart-candidates-off", {});
  await shoot(scheme, "chart-candidates-on", { press: true });
  await shoot(scheme, "chart-panes-live-no-data", { section: "Lower pane" });
  await shoot(scheme, "chart-panes-some-data", { stub: true, section: "Lower pane" });
}
await browser.close();
