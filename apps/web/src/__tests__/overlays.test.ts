// @trace: REQ-US-002
//
// PRD section 27.2's layers, carried by the deep link. REQ-US-002 asks that
// "all overlays active at signal time are restored"; these are the two halves
// that can be wrong -- reading the list, and deciding where the chart looks.

import { describe, expect, it } from "vitest";

import { overlaysFromQuery, RESTORED, NOT_RECORDED, UNREADABLE } from "../overlays";
import { DEFAULT_OVERLAYS } from "../types";
import { visibleRangeFor } from "../series";
import type { BarOut } from "../types";

const SECOND_NS = 1_000_000_000;
const MINUTE_NS = 60 * SECOND_NS;
const BASE_NS = 1788838800000000000;

function bars(count: number): BarOut[] {
  return Array.from({ length: count }, (_, i) => ({
    open_time_ns: BASE_NS + i * MINUTE_NS,
    close_time_ns: BASE_NS + (i + 1) * MINUTE_NS,
    open: "1",
    high: "1",
    low: "1",
    close: "1",
    volume_base: "1",
    is_final: true,
  }));
}

describe("reading the overlay list", () => {
  it("restores exactly the layers the link names", () => {
    // SC-004. The point of the parameter.
    const read = overlaysFromQuery(new URLSearchParams("overlays=candles,volume_profile"));

    expect(read.state).toBe(RESTORED);
    expect(read.overlays).toEqual(["candles", "volume_profile"]);
  });

  it("says the set was not recorded when the parameter is absent", () => {
    // SC-005, FR-005. Every alert sent before this feature existed has no
    // parameter, and those charts must not claim to have been restored.
    const read = overlaysFromQuery(new URLSearchParams("tf=15m"));

    expect(read.state).toBe(NOT_RECORDED);
    expect(read.overlays).toEqual([...DEFAULT_OVERLAYS]);
  });

  it("discards a list containing anything it does not recognise", () => {
    // SC-005, FR-006, and ADR-020's rule applied to a second parameter. A
    // restored subset looks restored while missing whichever layer the reader
    // most needed -- and nothing on screen would say which one went.
    const read = overlaysFromQuery(
      new URLSearchParams("overlays=candles,teleporter,volume_profile"),
    );

    expect(read.state).toBe(UNREADABLE);
    expect(read.overlays).toEqual([...DEFAULT_OVERLAYS]);
  });

  it("draws a duplicated layer once", () => {
    // FR-007. A repeat is sloppy, not corrupt; discarding the link over it
    // would lose a state that was perfectly readable.
    const read = overlaysFromQuery(new URLSearchParams("overlays=candles,candles"));

    expect(read.state).toBe(RESTORED);
    expect(read.overlays).toEqual(["candles"]);
  });

  it("treats an empty list as recorded-and-empty, not as absent", () => {
    // A link saying "no layers were on" is a statement. Falling back to the
    // defaults here would overrule it with a guess.
    const read = overlaysFromQuery(new URLSearchParams("overlays="));

    expect(read.state).toBe(RESTORED);
    expect(read.overlays).toEqual([]);
  });
});

describe("where the chart looks", () => {
  it("centres the visible range on the bar covering the instant", () => {
    // SC-006, FR-008. REQ-US-002 says "exactly the signal's timestamp"; a view
    // fitted to 500 bars contains that instant and hides it.
    const range = visibleRangeFor(bars(101), BASE_NS + 50 * MINUTE_NS, 10);

    expect(range).toEqual({ from: 45, to: 55 });
  });

  it("shows the whole history when the instant is outside it", () => {
    // SC-007, FR-009. Centring on a bar that does not exist would scroll the
    // chart to empty space and look like a data outage.
    expect(visibleRangeFor(bars(20), BASE_NS - MINUTE_NS, 10)).toBeNull();
    expect(visibleRangeFor(bars(20), BASE_NS + 500 * MINUTE_NS, 10)).toBeNull();
  });

  it("keeps the range inside the data at the edges", () => {
    // FR-010. A range running past the last bar leaves the signal off-centre
    // with blank space beside it, which reads as missing data.
    expect(visibleRangeFor(bars(20), BASE_NS, 10)).toEqual({ from: 0, to: 10 });
    expect(visibleRangeFor(bars(20), BASE_NS + 19 * MINUTE_NS, 10)).toEqual({
      from: 9,
      to: 19,
    });
  });

  it("does not ask for more bars than exist", () => {
    // FR-010. A history shorter than the focus window -- a new listing, or the
    // start of a backfill. A range running to bar 10 of five would leave the
    // chart showing blank space beside the signal, which reads as missing data
    // rather than as a short history.
    expect(visibleRangeFor(bars(5), BASE_NS + 2 * MINUTE_NS, 10)).toEqual({ from: 0, to: 4 });
  });

  it("has nothing to centre on when there are no bars", () => {
    expect(visibleRangeFor([], BASE_NS, 10)).toBeNull();
  });

  it("shows the whole history when no instant is given", () => {
    // FR-008 is about a link that carries one. A link without an instant is
    // section 27.1's plain chart route.
    expect(visibleRangeFor(bars(20), null, 10)).toBeNull();
  });
});
