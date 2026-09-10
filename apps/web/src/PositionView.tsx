// @trace: REQ-WP-032
//
// PRD section 44A.33's "Position page/chart", attached to the page.
//
// This component decides nothing. Which proposals are shown, which are holds,
// which levels exist and what to say when a path cannot be trusted -- all of
// that is `stopPath.ts`, where it is tested. Here it is four levels, a
// staircase and the reasons.
//
// The staircase is drawn with `stepAfter` semantics on purpose: a stop holds
// its price until a decision moves it, and interpolating between two proposals
// would draw a stop gliding upward through prices it never sat at. That is the
// prettier trail section 44A.33 forbids, reintroduced by a drawing choice.

import type { StopPathView } from "./stopPath";

const WIDTH = 720;
const HEIGHT = 200;

export function PositionView({
  view,
  failure = null,
}: {
  view: StopPathView;
  /** A load that failed. Never drawn as an empty path -- REQ-WP-009's FR-016. */
  failure?: string | null;
}): JSX.Element {
  return (
    <section aria-label="Stop path">
      <dl aria-label="Levels">
        {view.levels.map((level) => (
          <div key={level.label}>
            <dt>{level.label}</dt>
            <dd>{level.price}</dd>
          </div>
        ))}
      </dl>

      <dl aria-label="Risk">
        <div>
          <dt>open risk R</dt>
          <dd>{view.openRiskR === null ? "unavailable" : view.openRiskR.toFixed(2)}</dd>
        </div>
        <div>
          <dt>locked profit R</dt>
          <dd>{view.lockedProfitR.toFixed(2)}</dd>
        </div>
        {/* Unavailable, never "0.00". An excursion over nothing observed is not
            a flat one, and a zero here reads as a position that never moved. */}
        <div>
          <dt>MFE R</dt>
          <dd>{view.mfeR === null ? "unavailable" : view.mfeR.toFixed(2)}</dd>
        </div>
        <div>
          <dt>MAE R</dt>
          <dd>{view.maeR === null ? "unavailable" : view.maeR.toFixed(2)}</dd>
        </div>
      </dl>

      {failure === null ? null : (
        <p role="status" aria-label="Stop path load">
          Could not load the stop path: {failure}
        </p>
      )}
      {failure === null && view.state !== "ok" ? (
        <p role="status" aria-label="Stop path contents">
          {view.note}
        </p>
      ) : null}
      {failure === null && view.state === "ok" ? (
        <>
          <svg
            width={WIDTH}
            height={HEIGHT}
            role="img"
            aria-label={`stop path over ${view.path.length} decision(s)`}
          >
            <polyline
              fill="none"
              stroke="currentColor"
              strokeWidth="1"
              points={staircase(view, WIDTH, HEIGHT)}
            />
          </svg>
          <ol aria-label="Stop decisions">
            {view.path.map((point) => (
              <li key={point.at_ns} data-kind={point.kind}>
                <span>{point.price}</span>
                {/* The anchor is shown as missing rather than omitted: a hold
                    with nothing knowable is a fact about the market, and an
                    empty slot reads as an unrendered field. */}
                <span>{point.anchor === null ? "no anchor" : point.anchor.description}</span>
                <ul>
                  {point.reasons.map((reason) => (
                    <li key={reason}>{reason}</li>
                  ))}
                </ul>
              </li>
            ))}
          </ol>
        </>
      ) : null}
    </section>
  );
}

function staircase(view: StopPathView, width: number, height: number): string {
  const times = view.path.map((p) => p.at_ns);
  const prices = view.path.map((p) => Number(p.price));
  const [t0, t1] = [Math.min(...times), Math.max(...times)];
  const [p0, p1] = [Math.min(...prices), Math.max(...prices)];
  // A path that never moved gives a zero span in price, and a single decision
  // gives one in time. Centring both is the honest picture; dividing by zero
  // draws nothing, which would look like the empty state this view keeps apart.
  const spanT = t1 - t0 || 1;
  const spanP = p1 - p0 || 1;

  const points: string[] = [];
  let previousY: number | null = null;
  view.path.forEach((point) => {
    const x = ((point.at_ns - t0) / spanT) * width;
    const y = height - ((Number(point.price) - p0) / spanP) * height;
    // The corner: hold the old price up to this instant, then step.
    if (previousY !== null) points.push(`${x.toFixed(2)},${previousY.toFixed(2)}`);
    points.push(`${x.toFixed(2)},${y.toFixed(2)}`);
    previousY = y;
  });
  return points.join(" ");
}
