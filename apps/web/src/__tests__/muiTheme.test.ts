// @trace: REQ-WP-083
//
// One theme, a pure function of the scheme and of Telegram's theme parameters. The interface follows it in
// light and dark, and inside Telegram it follows Telegram's colours where Telegram supplies them.

import { describe, expect, it } from "vitest";

import { buildTheme, contrastRatio } from "../muiTheme";

describe("buildTheme: the scheme", () => {
  it.each(["light", "dark"] as const)("the palette mode is %s", (scheme) => {
    expect(buildTheme(scheme).palette.mode).toBe(scheme);
  });

  it("is a pure function: the same inputs give the same palette", () => {
    const a = buildTheme("dark", { bg_color: "#212d3b" }).palette;
    const b = buildTheme("dark", { bg_color: "#212d3b" }).palette;

    expect(a.background).toEqual(b.background);
    expect(a.primary.main).toBe(b.primary.main);
  });

  it("uses the product's own violet as the primary colour when Telegram supplies none", () => {
    expect(buildTheme("light").palette.primary.main).toBe("#7c5cff");
    expect(buildTheme("dark").palette.primary.main).toBe("#7c5cff");
  });

  it("light and dark have different backgrounds", () => {
    expect(buildTheme("light").palette.background.default).not.toBe(
      buildTheme("dark").palette.background.default,
    );
  });
});

describe("buildTheme: Telegram's parameters", () => {
  const PARAMS = {
    bg_color: "#212d3b",
    secondary_bg_color: "#17212b",
    text_color: "#f5f5f5",
    hint_color: "#708499",
    button_color: "#5288c1",
    button_text_color: "#ffffff",
  };

  it("takes background, text, hint and button from Telegram", () => {
    const palette = buildTheme("dark", PARAMS).palette;

    expect(palette.background.paper).toBe("#212d3b");
    expect(palette.background.default).toBe("#17212b");
    expect(palette.text.primary).toBe("#f5f5f5");
    expect(palette.text.secondary).toBe("#708499");
    expect(palette.primary.main).toBe("#5288c1");
    expect(palette.primary.contrastText).toBe("#ffffff");
  });

  it("falls back to the theme's own colour for a parameter Telegram did not supply", () => {
    const palette = buildTheme("dark", { bg_color: "#212d3b" }).palette;

    expect(palette.background.paper).toBe("#212d3b");
    expect(palette.primary.main).toBe("#7c5cff");
    expect(palette.text.primary).toBe(buildTheme("dark").palette.text.primary);
  });

  it("ignores a value that is not a colour rather than putting it in a stylesheet", () => {
    const palette = buildTheme("light", { bg_color: "url(javascript:1)", text_color: "red; x" }).palette;

    expect(palette.background.paper).toBe(buildTheme("light").palette.background.paper);
    expect(palette.text.primary).toBe(buildTheme("light").palette.text.primary);
  });
});

describe("contrast", () => {
  it("a known pair: black on white is 21", () => {
    expect(contrastRatio("#000000", "#ffffff")).toBeCloseTo(21, 5);
  });

  it.each(["light", "dark"] as const)("text is readable on the background and on paper (%s)", (scheme) => {
    const { palette } = buildTheme(scheme);

    expect(contrastRatio(palette.text.primary, palette.background.default)).toBeGreaterThanOrEqual(4.5);
    expect(contrastRatio(palette.text.primary, palette.background.paper)).toBeGreaterThanOrEqual(4.5);
  });

  it("the secondary text is readable too (a hint nobody can read is not a hint)", () => {
    for (const scheme of ["light", "dark"] as const) {
      const { palette } = buildTheme(scheme);
      expect(contrastRatio(palette.text.secondary, palette.background.paper)).toBeGreaterThanOrEqual(4.5);
    }
  });

  it("the primary button text is readable on the primary colour", () => {
    for (const scheme of ["light", "dark"] as const) {
      const { palette } = buildTheme(scheme);
      expect(contrastRatio(palette.primary.contrastText, palette.primary.main)).toBeGreaterThanOrEqual(3);
    }
  });
});
