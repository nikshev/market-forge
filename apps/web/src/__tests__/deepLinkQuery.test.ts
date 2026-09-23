// @trace: REQ-WP-074
//
// The link's `tf` is the timeframe the chart opens at, and the default it falls
// back to is written in one place. Both halves matter: every alert this system
// sends carries such a link, and a second spelling of the default is how the
// two ends drift.

import { describe, expect, it } from "vitest";

import deepLinkSource from "../deepLink.ts?raw";
import { parseDeepLink, withMode, withTimeframe } from "../deepLink";
import { DEFAULT_TIMEFRAME } from "../timeframes";

function parse(search: string) {
  return parseDeepLink("/chart/binance/BTCUSDT", search);
}

describe("the deep link's timeframe", () => {
  it("is returned verbatim when the link names one", () => {
    expect(parse("?tf=4h")?.timeframe).toBe("4h");
    expect(parse("?tf=1m")?.timeframe).toBe("1m");
  });

  it("falls back to the documented default when the link names none", () => {
    expect(parse("")?.timeframe).toBe(DEFAULT_TIMEFRAME);
  });

  it("returns the first value when tf is repeated", () => {
    expect(parse("?tf=1h&tf=5m")?.timeframe).toBe("1h");
  });

  it("keeps an unparseable token, so the page can refuse it by name", () => {
    // The parser does not validate: validation is against the *deployment's*
    // offered set, which only the API knows. Dropping or rewriting the token
    // here would make the refusal impossible to state.
    expect(parse("?tf=7m")?.timeframe).toBe("7m");
    expect(parse("?tf=1M")?.timeframe).toBe("1M");
  });

  it("writes the default in one place, not twice", () => {
    expect(deepLinkSource).toContain("DEFAULT_TIMEFRAME");
    expect(deepLinkSource).not.toContain('"15m"');
  });
});


describe("writing the address back", () => {
  it("sets the timeframe and keeps every other parameter", () => {
    const result = withTimeframe("at=2026-09-14T00%3A00%3A00Z&tf=1h&signal=abc", "30m");
    const params = new URLSearchParams(result);

    expect(params.get("tf")).toBe("30m");
    expect(params.get("at")).toBe("2026-09-14T00:00:00Z");
    expect(params.get("signal")).toBe("abc");
  });

  it("replaces a repeated tf rather than adding a second", () => {
    const params = new URLSearchParams(withTimeframe("tf=1h&tf=5m", "30m"));

    expect(params.getAll("tf")).toEqual(["30m"]);
  });

  it("writes as_seen_then=false for the refit and removes it for the default", () => {
    const refit = new URLSearchParams(withMode("tf=1h", "CURRENT REFIT"));
    expect(refit.get("as_seen_then")).toBe("false");
    expect(refit.get("tf")).toBe("1h");

    const original = new URLSearchParams(withMode("tf=1h&as_seen_then=false", "AS-SEEN-THEN"));
    expect(original.get("as_seen_then")).toBeNull();
    expect(original.get("tf")).toBe("1h");
  });

  it("does not touch the overlay parameters", () => {
    const params = new URLSearchParams(withTimeframe("overlays=candles%2Cchannel&tf=1h", "4h"));

    expect(params.get("overlays")).toBe("candles,channel");
  });
});
