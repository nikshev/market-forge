// @trace: REQ-WP-075
//
// The two rules that are easiest to get subtly wrong: the bytes of the
// destination link, and what "unscored" means. Both are pure functions so
// they can be asserted without a renderer.

import { describe, expect, it } from "vitest";

import { parseDeepLink } from "../deepLink";
import { marketHref, scoreLabel } from "../markets";

describe("the destination of a market", () => {
  it("is exactly the deep link a reader could paste", () => {
    expect(marketHref("binance", "BTCUSDT", "15m")).toBe("/chart/binance/BTCUSDT?tf=15m");
    expect(marketHref("binance", "ETHUSDT", "4h")).toBe("/chart/binance/ETHUSDT?tf=4h");
  });

  it("encodes path segments and the parser decodes them back", () => {
    const href = marketHref("binance", "A B/C", "1h");
    expect(href).toBe("/chart/binance/A%20B%2FC?tf=1h");

    const [path, search] = href.split("?");
    expect(parseDeepLink(path!, `?${search}`)?.symbol).toBe("A B/C");
  });
});

describe("what a score reads as", () => {
  it("renders null as unscored, never as zero", () => {
    expect(scoreLabel(null)).toBe("unscored");
  });

  it("renders a real zero as a score", () => {
    // Zero is a value: the market was examined and found worthless. That is a
    // different claim from "not examined", and this is where it stays one.
    expect(scoreLabel(0)).toBe("0.00");
  });

  it("renders a score with two decimals", () => {
    expect(scoreLabel(0.834)).toBe("0.83");
    expect(scoreLabel(-1)).toBe("-1.00");
  });
});
