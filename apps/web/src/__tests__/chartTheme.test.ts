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

describe("chartLayout with the theme's palette (REQ-WP-083)", () => {
  const PALETTE = { background: "#1c1c21", text: "#c9c9d1", grid: "#2c2c34" };

  it("dark takes the theme's own colours, not a second hard-coded set", () => {
    const layout = chartLayout("dark", PALETTE);

    expect(layout.layout?.background).toEqual({ type: "solid", color: "#1c1c21" });
    expect(layout.layout?.textColor).toBe("#c9c9d1");
    expect(layout.grid?.vertLines?.color).toBe("#2c2c34");
  });

  it("light with a palette matches the surface it sits on", () => {
    const layout = chartLayout("light", { background: "#ffffff", text: "#1a1d21", grid: "#e6e8eb" });

    expect(layout.layout?.background).toEqual({ type: "solid", color: "#ffffff" });
    expect(layout.layout?.textColor).toBe("#1a1d21");
  });

  it("light with no palette is still empty: the chart outside the new theme is unchanged", () => {
    expect(chartLayout("light")).toEqual({});
  });
});
