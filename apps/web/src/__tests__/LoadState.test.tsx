// @trace: REQ-WP-009
//
// FR-015 and FR-016. Three things look identical on a chart and mean entirely
// different things: no data in this range, data that failed to load, and data
// that is no longer arriving. A blank chart that means "broken" and a blank
// chart that means "quiet market" must not look the same.
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { LoadState } from "../LoadState";

describe("load state", () => {
  it("distinguishes an empty range from a failure", () => {
    const { unmount } = render(<LoadState state="empty" />);
    expect(screen.getByText(/no bars in this range/i)).toBeVisible();
    unmount();

    render(<LoadState state="failed" detail="connection refused" />);
    expect(screen.getByText(/could not be loaded/i)).toBeVisible();
    expect(screen.getByText(/connection refused/i)).toBeVisible();
  });

  it("says when the chart is no longer live", () => {
    // The same failure PRD section 25.6 forbids for alerts: a stale view that
    // looks current is worse than an obviously broken one.
    render(<LoadState state="disconnected" />);

    expect(screen.getByText(/no longer live/i)).toBeVisible();
  });

  it("renders nothing at all when the data is fine", () => {
    const { container } = render(<LoadState state="ok" />);

    expect(container).toBeEmptyDOMElement();
  });

  it("names the failure rather than only reporting one", () => {
    // "Something went wrong" sends a reader to the console. The detail is what
    // makes the message actionable.
    render(<LoadState state="failed" detail="HTTP 503" />);

    expect(screen.getByText(/HTTP 503/)).toBeVisible();
  });
});
