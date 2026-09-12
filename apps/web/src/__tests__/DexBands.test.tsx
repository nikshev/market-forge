// @trace: REQ-WP-059
//
// The layer from PRD section 27.2, and the judgement about age that nothing was
// making: `depthAgeNs` computed a gap and left the decision to a caller, and
// there was no caller.

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { chainFromQuery, parseDeepLink } from "../deepLink";
import { DexBands } from "../DexBands";
import {
  AHEAD,
  depthFreshness,
  depthOverlay,
  freshnessNotice,
  FRESH,
  STALE,
  STALE_AFTER_NS,
  UNKNOWN,
  UP,
  DOWN,
} from "../dexDepth";
import type { DexDepthBandOut, DexDepthResponse } from "../types";

const STATE_TIME = 1_700_000_000_000_000_000n;
const SECOND = 1_000_000_000n;

function band(overrides: Partial<DexDepthBandOut> = {}): DexDepthBandOut {
  return {
    side: UP,
    target_bps: "10",
    reachable: true,
    reached_bps: "10",
    amount0: "1.25",
    amount1: "3750.5",
    reference_price: "3000.1666",
    ticks_crossed: 4,
    reason: "",
    ...overrides,
  };
}

function overlayOf(bands: DexDepthBandOut[], stateTimeNs: bigint | null = STATE_TIME) {
  const value: DexDepthResponse = {
    chain_id: 1,
    pool: "0xpool",
    requested_at_ns: String(STATE_TIME),
    state_time_ns: bands.length === 0 || stateTimeNs === null ? null : String(stateTimeNs),
    bands,
  };
  return depthOverlay({ ok: true, value });
}

describe("how old is too old", () => {
  it("calls a curve within the threshold fresh and says nothing about it", () => {
    const overlay = overlayOf([band()]);
    const freshness = depthFreshness(overlay, STATE_TIME + 30n * SECOND, STALE_AFTER_NS);

    expect(freshness.state).toBe(FRESH);
    // A notice on every chart is a notice nobody reads.
    expect(freshnessNotice(freshness)).toBeNull();
  });

  it("is a boundary, and the boundary itself is fresh", () => {
    const overlay = overlayOf([band()]);

    expect(depthFreshness(overlay, STATE_TIME + STALE_AFTER_NS, STALE_AFTER_NS).state).toBe(FRESH);
    expect(depthFreshness(overlay, STATE_TIME + STALE_AFTER_NS + 1n, STALE_AFTER_NS).state).toBe(
      STALE,
    );
  });

  it("reports a stale curve's age in whole units", () => {
    const overlay = overlayOf([band()]);
    const hour = depthFreshness(overlay, STATE_TIME + 7200n * SECOND, STALE_AFTER_NS);

    expect(hour.state).toBe(STALE);
    expect(freshnessNotice(hour)).toBe("this curve is 2h old");

    const minutes = depthFreshness(overlay, STATE_TIME + 300n * SECOND, STALE_AFTER_NS);
    expect(freshnessNotice(minutes)).toBe("this curve is 5m old");
  });

  it("keeps the arithmetic in bigint, so a nanosecond age is not quantised", () => {
    const overlay = overlayOf([band()]);
    // 1.7e18 + 5000 read as a JavaScript number comes back 5120 later.
    const freshness = depthFreshness(overlay, STATE_TIME + 5_000n, STALE_AFTER_NS);

    expect(freshness.ageNs).toBe(5_000n);
  });

  it("says a curve carrying no time cannot be aged", () => {
    const freshness = depthFreshness(overlayOf([band()], null), STATE_TIME, STALE_AFTER_NS);

    expect(freshness.state).toBe(UNKNOWN);
    expect(freshness.ageNs).toBeNull();
    expect(freshnessNotice(freshness)).toMatch(/carries no time/);
  });

  it("calls out a curve later than the instant it is drawn at", () => {
    // Principle I on screen: a chart at an earlier instant showing a curve from
    // a later one is showing a reader what that moment could not have known. A
    // magnitude comparison would have called this fresh.
    const freshness = depthFreshness(overlayOf([band()]), STATE_TIME - 90n * SECOND, STALE_AFTER_NS);

    expect(freshness.state).toBe(AHEAD);
    expect(freshness.ageNs).toBe(-90n * SECOND);
    expect(freshnessNotice(freshness)).toBe("this curve is 1m later than the instant shown");
  });
});

describe("the layer", () => {
  it("draws nothing at all when it is off", () => {
    const { container } = render(
      <DexBands overlay={overlayOf([band()])} atNs={STATE_TIME} visible={false} />,
    );

    // Not an empty frame and not a notice explaining that it is off.
    expect(container).toBeEmptyDOMElement();
  });

  it("draws every band of the response, grouped by side", () => {
    const overlay = overlayOf([
      band({ target_bps: "25" }),
      band({ target_bps: "10" }),
      band({ side: DOWN, target_bps: "10" }),
    ]);
    render(<DexBands overlay={overlay} atNs={STATE_TIME} visible />);

    expect(screen.getByLabelText("Depth Above")).toBeInTheDocument();
    expect(screen.getByLabelText("Depth Below")).toBeInTheDocument();
    expect(screen.getAllByRole("row")).toHaveLength(5); // two headers, three bands
  });

  it("orders a side's bands by increasing distance", () => {
    const overlay = overlayOf([band({ target_bps: "100" }), band({ target_bps: "10" })]);
    render(<DexBands overlay={overlay} atNs={STATE_TIME} visible />);

    const rows = screen.getAllByRole("rowheader").map((cell) => cell.textContent);
    expect(rows).toEqual(["10 bps", "100 bps"]);
  });

  it("distinguishes an exhausted band without a reader reading a number", () => {
    const overlay = overlayOf([
      band({ target_bps: "10" }),
      band({ target_bps: "100", reachable: false, reached_bps: "17.5" }),
    ]);
    render(<DexBands overlay={overlay} atNs={STATE_TIME} visible />);

    expect(screen.getByLabelText(/100 bps — not reached, book exhausted at 17.5 bps/)).toBeVisible();
    expect(screen.getByLabelText("10 bps — reached")).toBeVisible();
  });

  it("keeps a failed load and an empty pool apart", () => {
    const failed = depthOverlay({ ok: false, error: "HTTP 503" });
    const { unmount } = render(<DexBands overlay={failed} atNs={STATE_TIME} visible />);
    expect(screen.getByLabelText("Depth layer").textContent).toMatch(/could not be loaded/);
    expect(screen.queryAllByRole("row")).toHaveLength(0);
    unmount();

    render(<DexBands overlay={overlayOf([])} atNs={STATE_TIME} visible />);
    expect(screen.getByLabelText("Depth layer").textContent).toMatch(/no depth curve/);
  });

  it("marks a stale curve on the chart it is drawn on", () => {
    const overlay = overlayOf([band()]);
    render(<DexBands overlay={overlay} atNs={STATE_TIME + 3600n * SECOND} visible />);

    const notice = screen.getByLabelText("Depth freshness");
    expect(notice.textContent).toBe("this curve is 1h old");
    expect(notice.dataset.freshness).toBe(STALE);
    // Stale is drawn, not withheld: the curve is the most recent one there is.
    expect(screen.getAllByRole("rowheader")).toHaveLength(1);
  });

  it("says nothing about the age of a fresh curve", () => {
    render(<DexBands overlay={overlayOf([band()])} atNs={STATE_TIME + SECOND} visible />);

    expect(screen.queryByLabelText("Depth freshness")).toBeNull();
  });
});

describe("which pool the layer draws", () => {
  it("reads a chain and a pool from the link", () => {
    const link = parseDeepLink("/chart/binance/BTCUSDT", "?chain=999&pool=0xbe512f");

    expect(link?.chainId).toBe(999);
    expect(link?.pool).toBe("0xbe512f");
  });

  it("takes them together or not at all", () => {
    // A pool with no chain is not addressable; a chain with no pool asks for
    // nothing. Either alone would produce a request that could only fail, and
    // then a notice about a layer nobody could have.
    expect(parseDeepLink("/chart/binance/BTCUSDT", "?pool=0xbe512f")?.chainId).toBeNull();
    expect(parseDeepLink("/chart/binance/BTCUSDT", "?pool=0xbe512f")?.pool).toBeNull();
    expect(parseDeepLink("/chart/binance/BTCUSDT", "?chain=999")?.pool).toBeNull();
    expect(parseDeepLink("/chart/binance/BTCUSDT", "?chain=999")?.chainId).toBeNull();
  });

  it("refuses a chain id that is not one", () => {
    // `parseInt("12abc")` is 12, which would request depth from a chain nobody
    // named -- a real chain, with real pools, and the wrong one.
    for (const raw of ["12abc", "0", "-1", "1.5", "", " 999"]) {
      const link = parseDeepLink("/chart/binance/BTCUSDT", `?chain=${raw}&pool=0xbe512f`);
      expect(chainFromQuery(new URLSearchParams(`chain=${raw}`))).toBeNull();
      expect(link?.chainId).toBeNull();
    }
  });

  it("names no pool when the link names none", () => {
    const link = parseDeepLink("/chart/binance/BTCUSDT", "");

    expect(link?.chainId).toBeNull();
    expect(link?.pool).toBeNull();
  });
});
