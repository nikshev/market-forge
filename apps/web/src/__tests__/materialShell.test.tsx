// @trace: REQ-WP-083
//
// The shell: an app bar with the logo and the product's name, once, as the page's single level-one heading;
// and a way back from a chart in a browser (in Telegram its own back button does that).

import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { AppShell } from "../AppShell";

function telegram(on: boolean): void {
  (window as unknown as { Telegram?: unknown }).Telegram = on ? { WebApp: {} } : undefined;
}

afterEach(() => telegram(false));

describe("AppShell", () => {
  it("has exactly one level-one heading, the product's name", () => {
    render(<AppShell>content</AppShell>);

    const headings = screen.getAllByRole("heading", { level: 1 });
    expect(headings).toHaveLength(1);
    expect(headings[0]).toHaveTextContent("Market Forge");
  });

  it("shows the page inside a main landmark", () => {
    render(<AppShell>hello</AppShell>);

    expect(screen.getByRole("main")).toHaveTextContent("hello");
  });

  it("shows the logo as a decorative image, not a second name", () => {
    const { container } = render(<AppShell>x</AppShell>);

    const logo = container.querySelector("img");
    expect(logo).not.toBeNull();
    expect(logo?.getAttribute("src")).toBe("/logo.svg");
    expect(logo?.getAttribute("alt")).toBe("");
  });

  it("shows a way back when given one, in a browser", () => {
    render(<AppShell back="/">x</AppShell>);

    const back = screen.getByRole("link", { name: "Back to markets" });
    expect(back).toHaveAttribute("href", "/");
  });

  it("shows no way back when none is given", () => {
    render(<AppShell>x</AppShell>);

    expect(screen.queryByRole("link", { name: "Back to markets" })).toBeNull();
  });

  it("shows no way back inside Telegram, whose own back button does that", () => {
    telegram(true);

    render(<AppShell back="/">x</AppShell>);

    expect(screen.queryByRole("link", { name: "Back to markets" })).toBeNull();
  });
});
