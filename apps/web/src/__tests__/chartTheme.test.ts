// @trace: REQ-WP-080
//
// The chart takes the colour scheme. `lightweight-charts` cannot draw in jsdom, so the decision --
// what layout a scheme gets -- is a function and is what is tested, the way `buildSeries` is.

import { describe, expect, it } from "vitest";

import { chartLayout, schemeNow } from "../theme";

describe("chartLayout", () => {
  it("is empty for light, so outside Telegram the chart is exactly what it was", () => {
    expect(chartLayout("light")).toEqual({});
  });

  it("gives dark a dark background and a light text colour", () => {
    const layout = chartLayout("dark");

    expect(layout.layout?.background).toEqual({ type: "solid", color: expect.stringMatching(/^#[0-3]/) });
    expect(layout.layout?.textColor).toMatch(/^#[c-f]/i);
  });

  it("darkens the grid too, or a dark chart has bright rules across it", () => {
    const grid = chartLayout("dark").grid;

    expect(grid?.vertLines?.color).toBeDefined();
    expect(grid?.horzLines?.color).toBeDefined();
  });
});

describe("schemeNow", () => {
  it("is light when nothing set a scheme", () => {
    document.documentElement.removeAttribute("data-scheme");

    expect(schemeNow()).toBe("light");
  });

  it("is what the page was given", () => {
    document.documentElement.dataset.scheme = "dark";

    expect(schemeNow()).toBe("dark");
    document.documentElement.removeAttribute("data-scheme");
  });
});
