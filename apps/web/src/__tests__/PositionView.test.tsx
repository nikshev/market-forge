// @trace: REQ-WP-032
//
// The component decides nothing -- `stopPath.test.ts` covers that. What is
// worth asserting here is what a reader sees and a decision module cannot: that
// an unavailable excursion is never printed as 0.00, that a path that cannot be
// trusted is not drawn, and that the line between two decisions is a staircase
// rather than a glide through prices the stop never sat at.

import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { PositionView } from "../PositionView";
import type { StopPathView } from "../stopPath";

const BASE_NS = 1788838800000000000;
const MINUTE_NS = 60 * 1_000_000_000;

function view(overrides: Partial<StopPathView> = {}): StopPathView {
  return {
    state: "ok",
    note: "2 recorded stop decisions",
    levels: [
      { label: "entry", price: "100.00" },
      { label: "initial", price: "90.00" },
      { label: "current", price: "95.00" },
    ],
    path: [
      {
        at_ns: BASE_NS,
        price: "92.00",
        kind: "moved",
        reasons: ["STRUCTURAL_ANCHOR"],
        anchor: {
          kind: "confirmed_swing",
          price: "92.00",
          known_at_ns: BASE_NS,
          description: "a confirmed higher low",
        },
      },
      {
        at_ns: BASE_NS + MINUTE_NS,
        price: "92.00",
        kind: "held",
        reasons: ["HELD_COOLDOWN"],
        anchor: null,
      },
    ],
    openRiskR: 0.8,
    lockedProfitR: 0,
    mfeR: null,
    maeR: null,
    ...overrides,
  };
}

describe("the stop path a reader sees", () => {
  it("says an unavailable excursion is unavailable, not zero", () => {
    render(<PositionView view={view()} />);

    const risk = screen.getByLabelText("Risk");
    expect(within(risk).getByText("MFE R").nextSibling).toHaveTextContent("unavailable");
    expect(within(risk).getByText("MAE R").nextSibling).toHaveTextContent("unavailable");
    // Locked profit is genuinely none, and says so as a number.
    expect(within(risk).getByText("locked profit R").nextSibling).toHaveTextContent("0.00");
  });

  it("draws nothing at all when the path cannot be trusted", () => {
    render(
      <PositionView
        view={view({ state: "inconsistent", path: [], note: "the proposal at 17 cites an anchor" })}
      />,
    );

    expect(screen.queryByRole("img")).toBeNull();
    expect(screen.getByLabelText("Stop path contents")).toHaveTextContent("cites an anchor");
  });

  it("never draws a failed load as an empty path", () => {
    render(<PositionView view={view({ state: "empty", path: [] })} failure="HTTP 503" />);

    expect(screen.getByLabelText("Stop path load")).toHaveTextContent("HTTP 503");
    expect(screen.queryByLabelText("Stop path contents")).toBeNull();
  });

  it("says nothing about loading when nothing failed", () => {
    // The other half of the rule above. A view that always shows the failure
    // line reads as permanently broken, and a mutant that always rendered it
    // survived a test asserting only that a real failure appears.
    render(<PositionView view={view()} />);

    expect(screen.queryByLabelText("Stop path load")).toBeNull();
  });

  it("still shows the levels and risk when there is no path", () => {
    // An unrun policy is not unknown risk -- the levels come from the position.
    render(<PositionView view={view({ state: "empty", path: [], note: "no path" })} />);

    expect(within(screen.getByLabelText("Levels")).getByText("100.00")).toBeInTheDocument();
    expect(
      within(screen.getByLabelText("Risk")).getByText("open risk R").nextSibling,
    ).toHaveTextContent("0.80");
  });

  it("steps between decisions instead of gliding through them", () => {
    // A stop holds its price until a decision moves it. An interpolated line
    // draws it sitting at prices it never sat at, which is the prettier trail
    // section 44A.33 forbids, reintroduced as a drawing choice.
    render(
      <PositionView
        view={view({
          path: [
            { at_ns: BASE_NS, price: "90.00", kind: "moved", reasons: ["A"], anchor: null },
            {
              at_ns: BASE_NS + MINUTE_NS,
              price: "95.00",
              kind: "moved",
              reasons: ["B"],
              anchor: null,
            },
          ],
        })}
      />,
    );

    const points = screen.getByRole("img").querySelector("polyline")?.getAttribute("points");
    // Three vertices for two decisions: the second x appears twice, once at the
    // old price and once at the new one. A glide would give two.
    expect(points?.split(" ")).toHaveLength(3);
    expect(points).toBe("0.00,200.00 720.00,200.00 720.00,0.00");
  });

  it("shows a hold as a hold, with its reason and its missing anchor", () => {
    render(<PositionView view={view()} />);

    const decisions = within(screen.getByLabelText("Stop decisions")).getAllByRole("listitem");
    const hold = decisions.find((li) => li.dataset.kind === "held");
    expect(hold).toBeDefined();
    expect(hold).toHaveTextContent("HELD_COOLDOWN");
    expect(hold).toHaveTextContent("no anchor");
  });
});
