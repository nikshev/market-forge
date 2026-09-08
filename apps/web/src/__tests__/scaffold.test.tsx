// @trace: REQ-WP-009
//
// The frontend suite exists before the frontend does (ADR-021, task T001): a
// CI step added after the code is a step written to pass what is already
// there. This asserts the harness works -- render, query, assert -- so a later
// failure is the component's, not the setup's.
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { App } from "../App";

describe("the frontend test harness", () => {
  it("renders a component and can query it", () => {
    render(<App />);
    expect(screen.getByRole("heading", { name: "ChannelFlow" })).toBeInTheDocument();
  });
});
