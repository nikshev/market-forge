// @trace: REQ-WP-090
//
// LoadState shows failed vocabulary on refresh failure, clears on success

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { LoadState } from "../LoadState";

describe("US3: LoadState vocabulary on refresh", () => {
  it("shows 'failed' with role=alert for refresh failure", () => {
    render(<LoadState state="failed" detail="Refresh failed: HTTP 500" />);

    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent("The data could not be loaded: Refresh failed: HTTP 500");
    expect(alert).not.toHaveTextContent("No bars in this range.");
  });

  it("shows 'empty' with role=status for empty market", () => {
    render(<LoadState state="empty" />);

    const status = screen.getByRole("status");
    expect(status).toHaveTextContent("No bars in this range.");
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("shows 'disconnected' with role=status for stopped updates", () => {
    render(<LoadState state="disconnected" />);

    const status = screen.getByRole("status");
    expect(status).toHaveTextContent("This chart is no longer live — updates have stopped.");
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("shows nothing for 'ok' state", () => {
    render(<LoadState state="ok" />);

    expect(screen.queryByRole("alert")).toBeNull();
    expect(screen.queryByRole("status")).toBeNull();
  });
});