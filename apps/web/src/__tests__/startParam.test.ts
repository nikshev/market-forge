// @trace: REQ-WP-080
//
// A Mini App link carries the chart state in a `start_param` (letters, digits, `_`, `-`; at most 512
// characters). PRD US-002 -- "press a button in Telegram and open the chart at the signal's timestamp"
// -- is why: the alert's button must land on the same state the query-string deep link does.

import { describe, expect, it } from "vitest";

import { parseDeepLink } from "../deepLink";
import { applyStartParam, decodeStartParam, encodeStartParam } from "../startParam";

const LINK =
  "/chart/binance/BTC-USDT-SWAP?tf=15m&at=2026-09-06T11:15:00Z" +
  "&signal=3f2b8c1e-9a4d-4e6f-8b7a-1c2d3e4f5a6b&mode=AS-SEEN-THEN" +
  "&overlays=candles,channel_lines,signal_marker,extrema,dex_liquidity_bands" +
  "&chain=143&pool=0x0123456789abcdef0123456789abcdef01234567";

function split(pathAndQuery: string): [string, string] {
  const at = pathAndQuery.indexOf("?");
  return at === -1 ? [pathAndQuery, ""] : [pathAndQuery.slice(0, at), pathAndQuery.slice(at)];
}

describe("both forms of a link give one chart state", () => {
  it("a start_param and the equivalent query string parse to the same state", () => {
    const fromParam = decodeStartParam(encodeStartParam(LINK));
    expect(fromParam).not.toBeNull();

    const [path, search] = split(LINK);
    const [pathB, searchB] = split(fromParam as string);

    expect(parseDeepLink(pathB, searchB)).toEqual(parseDeepLink(path, search));
  });

  it("the overview round-trips too", () => {
    expect(decodeStartParam(encodeStartParam("/"))).toBe("/");
  });
});

describe("what Telegram allows in a start_param", () => {
  it("the longest realistic link encodes to at most 512 characters", () => {
    expect(encodeStartParam(LINK).length).toBeLessThanOrEqual(512);
  });

  it("uses only letters, digits, underscore and hyphen", () => {
    expect(encodeStartParam(LINK)).toMatch(/^[A-Za-z0-9_-]+$/);
  });
});

describe("what is refused", () => {
  const evil = [
    "//evil.example/chart/x/y",
    "https://evil.example/",
    "javascript:alert(1)",
    "/chart/../admin",
    "/chart/binance",
    "/chart/binance/BTCUSDT/extra",
    "/api/v1/markets",
    "/chart/binance/BTCUSDT?tf=15m#frag",
    "/chart/binance/BTC USDT",
  ];

  it.each(evil)("%s opens the overview, not that", (value) => {
    expect(decodeStartParam(encodeStartParam(value))).toBeNull();
  });

  it.each(["", "!!!not base64!!!", "AAAA", "x".repeat(600), "%%%"])(
    "an unreadable value (%s) opens the overview",
    (value) => {
      expect(decodeStartParam(value)).toBeNull();
    },
  );
});

describe("applying it", () => {
  function address(path: string): void {
    window.history.replaceState(null, "", path);
  }

  it("puts the state in the address before the page reads it", () => {
    address("/");

    applyStartParam(encodeStartParam(LINK));

    expect(window.location.pathname + window.location.search).toBe(LINK);
  });

  it("leaves the address alone when it is unreadable", () => {
    address("/");

    applyStartParam("!!!");

    expect(window.location.pathname + window.location.search).toBe("/");
  });

  it("does not override a page that was opened at a chart", () => {
    address("/chart/bybit/BTCUSDT?tf=1h");

    applyStartParam(encodeStartParam(LINK));

    expect(window.location.pathname + window.location.search).toBe("/chart/bybit/BTCUSDT?tf=1h");
  });

  it("does nothing when there is no start parameter", () => {
    address("/");

    applyStartParam(null);

    expect(window.location.pathname).toBe("/");
  });
});
