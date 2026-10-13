// @trace: REQ-WP-103
//
// A page that is waiting says so (REQ-WP-103). The owner could not tell a bug from a slow load: empty areas looked identical in
// both. Every place the page waits has a spinner with a name, it goes away when the answer arrives -- whatever the answer is --
// and nothing that is not waiting shows one. Spinners are `progressbar`s, never `status`, so they cannot be mistaken for
// (or hide) the page's statements about the data.

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { Busy } from "../Busy";
import { FlowPane } from "../FlowPane";
import { LiveChip } from "../LiveChip";
import { Markets } from "../Markets";
import { ProfileControls } from "../ProfileControls";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("Busy", () => {
  it("is a named progress bar the page can be asked about", () => {
    render(<Busy label="Loading things" />);

    expect(screen.getByRole("progressbar", { name: "Loading things" })).toBeInTheDocument();
    expect(screen.getByText("Loading things")).toBeInTheDocument();
  });

  it("can be small and inline, with no text of its own", () => {
    render(<Busy label="Updating" inline />);

    expect(screen.getByRole("progressbar", { name: "Updating" })).toBeInTheDocument();
    expect(screen.queryByText("Updating")).toBeNull();
  });

  it("is not a status, so it never hides or imitates a statement about the data", () => {
    render(<Busy label="Loading things" />);

    expect(screen.queryByRole("status")).toBeNull();
  });
});

describe("the overview while it waits", () => {
  const never = (): Promise<Response> => new Promise(() => undefined);

  it("shows a spinner for the markets and for the timeframes until they answer", () => {
    vi.stubGlobal("fetch", never);

    render(<Markets />);

    expect(screen.getByRole("progressbar", { name: "Loading markets" })).toBeInTheDocument();
    expect(screen.getByRole("progressbar", { name: "Loading timeframes" })).toBeInTheDocument();
  });

  it("takes them away when the answers arrive", async () => {
    vi.stubGlobal("fetch", async (url: string) => {
      const body = String(url).includes("/timeframes")
        ? { timeframes: [{ token: "1m", timeframe_ns: 60_000_000_000 }] }
        : { markets: [] };
      return new Response(JSON.stringify(body), { status: 200 });
    });

    render(<Markets />);

    await waitFor(() => expect(screen.queryByRole("progressbar")).toBeNull());
  });

  it("takes them away when the answers are failures, and says so instead", async () => {
    vi.stubGlobal("fetch", async () => new Response("no", { status: 500 }));

    render(<Markets />);

    await waitFor(() => expect(screen.queryByRole("progressbar")).toBeNull());
    expect(screen.getAllByRole("alert").length).toBeGreaterThan(0);
  });
});

describe("a pane while it waits", () => {
  it("shows a spinner, and no claim about the data, until the series has answered", () => {
    render(<FlowPane points={[]} feature="ofi_1m" onSelect={() => {}} pointsLoaded={false} barsLoaded />);

    expect(screen.getByRole("progressbar", { name: "Loading the pane" })).toBeInTheDocument();
    expect(screen.queryByText(/no feature points|no readings/i)).toBeNull();
  });

  it("shows one for Volume until the bars have answered", () => {
    render(<FlowPane points={[]} feature="volume" onSelect={() => {}} barsLoaded={false} />);

    expect(screen.getByRole("progressbar", { name: "Loading the pane" })).toBeInTheDocument();
  });

  it("shows none once it has answered, even with nothing in it", () => {
    render(<FlowPane points={[]} feature="ofi_1m" onSelect={() => {}} pointsLoaded barsLoaded />);

    expect(screen.queryByRole("progressbar")).toBeNull();
    expect(screen.getByRole("status", { name: /Pane contents/ })).toBeInTheDocument();
  });

  it("shows none when the load failed: the failure is the answer", () => {
    render(<FlowPane points={[]} feature="ofi_1m" onSelect={() => {}} pointsLoaded failure="HTTP 500" barsLoaded />);

    expect(screen.queryByRole("progressbar")).toBeNull();
    expect(screen.getByRole("status", { name: "Pane load" })).toHaveTextContent("HTTP 500");
  });

  it("is unchanged for a caller that does not say (the default is: not waiting)", () => {
    render(<FlowPane points={[]} feature="ofi_1m" onSelect={() => {}} barsLoaded />);

    expect(screen.queryByRole("progressbar")).toBeNull();
  });
});

describe("the volume profile while it waits", () => {
  it("shows a spinner while loading and none once it is ok, none or failed", () => {
    const props = { window: "24h" as const, onWindow: () => undefined, profile: null };
    const { rerender } = render(<ProfileControls {...props} state="loading" />);
    expect(screen.getByRole("progressbar", { name: "Loading the volume profile" })).toBeInTheDocument();

    for (const state of ["ok", "none", "failed"] as const) {
      rerender(<ProfileControls {...props} state={state} failure="x" />);
      expect(screen.queryByRole("progressbar")).toBeNull();
    }
  });
});

describe("the live chip while it connects", () => {
  it("shows a spinner and says connecting, not delayed, before the feed has spoken", () => {
    render(<LiveChip status="connecting" />);

    const chip = screen.getByRole("status", { name: "Live feed" });
    expect(chip).toHaveTextContent(/connecting/i);
    expect(chip).not.toHaveTextContent(/delayed/i);
    expect(screen.getByRole("progressbar", { name: "Connecting to the live feed" })).toBeInTheDocument();
  });

  it("shows no spinner when live, delayed or off", () => {
    for (const status of ["live", "delayed", "off"] as const) {
      const { unmount } = render(<LiveChip status={status} />);
      expect(screen.queryByRole("progressbar")).toBeNull();
      unmount();
    }
  });
});

void userEvent;
