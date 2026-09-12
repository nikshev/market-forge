// @trace: REQ-WP-059
//
// PRD section 27.2's `DEX liquidity bands` layer, attached to the page.
//
// This component decides nothing. Which bands exist, which side they are on,
// whether the walk reached its target, how old the curve is and what to say
// about it -- all of that is `dexDepth.ts`, where it is tested.
//
// It is a table rather than a line on the chart's canvas, for the reason
// `panes.ts` gives about jsdom: a component test can see a cell and can never
// see a stroke. The part a reader acts on is the numbers and the distinction
// between a band the book reached and one where it ran out, and both are here.

import {
  bandsForSide,
  depthFreshness,
  DOWN,
  EXHAUSTED,
  FAILED,
  freshnessNotice,
  NO_CURVE,
  STALE_AFTER_NS,
  UP,
  type DepthBand,
  type DepthOverlay,
} from "./dexDepth";

const SIDE_LABEL: Record<string, string> = {
  [UP]: "Above",
  [DOWN]: "Below",
};

export function DexBands({
  overlay,
  atNs,
  visible,
  staleAfterNs = STALE_AFTER_NS,
}: {
  overlay: DepthOverlay;
  /** The instant the chart is showing, against which the curve is aged. */
  atNs: bigint;
  /** Whether `dex_liquidity_bands` is among the selected overlays. */
  visible: boolean;
  staleAfterNs?: bigint;
}): JSX.Element | null {
  // A layer that is off shows nothing at all -- not an empty frame and not a
  // notice explaining that it is off. A reader turned it off.
  if (!visible) {
    return null;
  }

  // FAILED and NO_CURVE carry their own words and never a band between them:
  // REQ-WP-009's FR-016, which the overlay already separates and which a single
  // blank layer here would quietly undo.
  if (overlay.state === FAILED || overlay.state === NO_CURVE) {
    return (
      <section aria-label="DEX liquidity bands">
        <p role="status" aria-label="Depth layer">
          {overlay.notice}
        </p>
      </section>
    );
  }

  const freshness = depthFreshness(overlay, atNs, staleAfterNs);
  const notice = freshnessNotice(freshness);
  const sides = [UP, DOWN].filter((side) => bandsForSide(overlay, side).length > 0);

  return (
    <section aria-label="DEX liquidity bands">
      {notice === null ? null : (
        <p role="status" aria-label="Depth freshness" data-freshness={freshness.state}>
          {notice}
        </p>
      )}
      {sides.map((side) => (
        <table key={side} aria-label={`Depth ${SIDE_LABEL[side] ?? side}`}>
          <thead>
            <tr>
              <th scope="col">Target</th>
              <th scope="col">Reached</th>
              <th scope="col">Amount in</th>
              <th scope="col">Amount out</th>
            </tr>
          </thead>
          <tbody>
            {bandsForSide(overlay, side).map((band) => (
              <BandRow key={`${side}-${band.targetBps}`} band={band} />
            ))}
          </tbody>
        </table>
      ))}
    </section>
  );
}

function BandRow({ band }: { band: DepthBand }): JSX.Element {
  const exhausted = band.role === EXHAUSTED;
  return (
    <tr
      // The distinction a reader must be able to make without reading a number:
      // a band the walk reached and one where the book ran out first describe
      // opposite markets and are the same shape (ADR-036).
      data-role={band.role}
      aria-label={
        exhausted
          ? `${band.targetBps} bps — not reached, book exhausted at ${band.reachedBps} bps`
          : `${band.targetBps} bps — reached`
      }
    >
      <th scope="row">{band.targetBps} bps</th>
      <td>{exhausted ? `exhausted at ${band.reachedBps} bps` : "reached"}</td>
      <td>{band.amount0}</td>
      <td>{band.amount1}</td>
    </tr>
  );
}
