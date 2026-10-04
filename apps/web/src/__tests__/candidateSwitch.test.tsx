// @trace: REQ-WP-084

import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { CandidateSwitch } from "../CandidateSwitch";

describe("the candidate extrema switch", () => {
  it("is a button named for what it shows, off to begin with", () => {
    render(<CandidateSwitch pressed={false} onChange={() => {}} />);

    expect(screen.getByRole("button", { name: "Candidate extrema" })).toHaveAttribute(
      "aria-pressed",
      "false",
    );
  });

  it("exposes the on state to assistive technology", () => {
    render(<CandidateSwitch pressed onChange={() => {}} />);

    expect(screen.getByRole("button", { name: "Candidate extrema" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
  });

  it("asks for the opposite of its state when pressed, both ways", () => {
    const onChange = vi.fn();
    const { rerender } = render(<CandidateSwitch pressed={false} onChange={onChange} />);

    fireEvent.click(screen.getByRole("button", { name: "Candidate extrema" }));
    expect(onChange).toHaveBeenLastCalledWith(true);

    rerender(<CandidateSwitch pressed onChange={onChange} />);
    fireEvent.click(screen.getByRole("button", { name: "Candidate extrema" }));
    expect(onChange).toHaveBeenLastCalledWith(false);
  });
});
