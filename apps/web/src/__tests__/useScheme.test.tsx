// @trace: REQ-WP-083
//
// Where the colour scheme comes from: Telegram's inside Telegram, the browser's outside.

import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { useScheme } from "../useScheme";

type Listener = (event: { matches: boolean }) => void;

function mockMedia(initialDark: boolean): { set: (dark: boolean) => void } {
  let dark = initialDark;
  const listeners = new Set<Listener>();
  window.matchMedia = ((query: string) => ({
    // A getter: MUI keeps the list it was given and reads `matches` from it on every change.
    get matches() {
      return query.includes("dark") ? dark : false;
    },
    media: query,
    onchange: null,
    addEventListener: (_: string, listener: Listener) => listeners.add(listener),
    removeEventListener: (_: string, listener: Listener) => listeners.delete(listener),
    addListener: (listener: Listener) => listeners.add(listener),
    removeListener: (listener: Listener) => listeners.delete(listener),
    dispatchEvent: () => true,
  })) as unknown as typeof window.matchMedia;
  return {
    set: (next: boolean) => {
      dark = next;
      listeners.forEach((listener) => listener({ matches: next }));
    },
  };
}

function telegram(scheme: "light" | "dark" | undefined): void {
  (window as unknown as { Telegram?: unknown }).Telegram =
    scheme === undefined ? undefined : { WebApp: { colorScheme: scheme, themeParams: {} } };
}

beforeEach(() => telegram(undefined));
afterEach(() => telegram(undefined));

describe("useScheme", () => {
  it("outside Telegram follows the browser: dark", () => {
    mockMedia(true);

    expect(renderHook(() => useScheme()).result.current).toBe("dark");
  });

  it("outside Telegram follows the browser: light", () => {
    mockMedia(false);

    expect(renderHook(() => useScheme()).result.current).toBe("light");
  });

  it("inside Telegram follows Telegram, not the browser", () => {
    mockMedia(false);
    telegram("dark");

    expect(renderHook(() => useScheme()).result.current).toBe("dark");
  });

  it("inside Telegram a light scheme wins over a dark browser", () => {
    mockMedia(true);
    telegram("light");

    expect(renderHook(() => useScheme()).result.current).toBe("light");
  });

  it("follows the browser when it changes while the page is open", () => {
    const media = mockMedia(false);
    const { result } = renderHook(() => useScheme());
    expect(result.current).toBe("light");

    act(() => media.set(true));

    expect(result.current).toBe("dark");
  });
});
