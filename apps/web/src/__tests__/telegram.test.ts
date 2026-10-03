// @trace: REQ-WP-080
//
// The page as a Telegram Mini App, against a stand-in for `window.Telegram.WebApp`, and as itself
// without one. Outside Telegram nothing may change: no request to telegram.org, no header, no throw.

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { fetchTimeframes } from "../api";
import {
  authorizationHeader,
  initMiniApp,
  launchData,
  launchedFromTelegram,
  loadTelegramScript,
} from "../telegram";

const LAUNCH = "query_id=AAx&auth_date=1790000000&hash=abc";

interface StandIn {
  initData: string;
  colorScheme: "light" | "dark";
  themeParams: Record<string, string>;
  ready: ReturnType<typeof vi.fn>;
  expand: ReturnType<typeof vi.fn>;
  disableVerticalSwipes?: ReturnType<typeof vi.fn>;
  BackButton?: {
    show: ReturnType<typeof vi.fn>;
    hide: ReturnType<typeof vi.fn>;
    onClick: ReturnType<typeof vi.fn>;
    offClick: ReturnType<typeof vi.fn>;
  };
}

function standIn(overrides: Partial<StandIn> = {}): StandIn {
  return {
    initData: LAUNCH,
    colorScheme: "dark",
    themeParams: { bg_color: "#17212b", text_color: "#f5f5f5", hint_color: "#708499" },
    ready: vi.fn(),
    expand: vi.fn(),
    disableVerticalSwipes: vi.fn(),
    BackButton: { show: vi.fn(), hide: vi.fn(), onClick: vi.fn(), offClick: vi.fn() },
    ...overrides,
  };
}

function install(app: StandIn | undefined): void {
  (window as unknown as { Telegram?: unknown }).Telegram = app === undefined ? undefined : { WebApp: app };
}

function at(path: string): void {
  window.history.replaceState(null, "", path);
}

beforeEach(() => {
  install(undefined);
  at("/");
  document.documentElement.removeAttribute("style");
  document.documentElement.removeAttribute("data-scheme");
  document.head.querySelectorAll("script[data-telegram]").forEach((node) => node.remove());
  vi.restoreAllMocks();
});

afterEach(() => {
  install(undefined);
});

describe("inside Telegram", () => {
  it("tells Telegram it is ready and expands, once each, however often it is initialised", () => {
    const app = standIn();
    install(app);

    initMiniApp();
    initMiniApp();

    expect(app.ready).toHaveBeenCalledTimes(1);
    expect(app.expand).toHaveBeenCalledTimes(1);
  });

  it("disables vertical swipes, which otherwise swallow the touches meant for the chart", () => {
    const app = standIn();
    install(app);

    initMiniApp();

    expect(app.disableVerticalSwipes).toHaveBeenCalledTimes(1);
  });

  it("applies Telegram's theme parameters and colour scheme", () => {
    install(standIn());

    initMiniApp();

    const root = document.documentElement;
    expect(root.style.getPropertyValue("--tg-bg")).toBe("#17212b");
    expect(root.style.getPropertyValue("--tg-text")).toBe("#f5f5f5");
    expect(root.dataset.scheme).toBe("dark");
  });

  it("shows the back button on a chart and a press returns to the overview", () => {
    const app = standIn();
    install(app);
    at("/chart/binance/BTCUSDT?tf=15m");
    const navigate = vi.fn();

    initMiniApp({ navigate });

    expect(app.BackButton?.show).toHaveBeenCalledTimes(1);
    const press = app.BackButton?.onClick.mock.calls[0]?.[0] as () => void;
    press();
    expect(navigate).toHaveBeenCalledWith("/");
  });

  it("does not show the back button on the overview", () => {
    const app = standIn();
    install(app);
    at("/");

    initMiniApp({ navigate: vi.fn() });

    expect(app.BackButton?.show).not.toHaveBeenCalled();
    expect(app.BackButton?.hide).toHaveBeenCalled();
  });

  it("sends the launch data with every API request", async () => {
    install(standIn());
    const seen: RequestInit[] = [];
    vi.stubGlobal("fetch", async (_url: string, init?: RequestInit) => {
      seen.push(init ?? {});
      return new Response(JSON.stringify({ timeframes: [] }), { status: 200 });
    });

    await fetchTimeframes();
    await fetchTimeframes();

    expect(seen).toHaveLength(2);
    for (const init of seen) {
      expect(init.headers).toEqual({ Authorization: `tma ${LAUNCH}` });
    }
    vi.unstubAllGlobals();
  });

  it("copes with an older client that has no back button and no swipe call", () => {
    const app = standIn({ BackButton: undefined, disableVerticalSwipes: undefined });
    install(app);
    at("/chart/binance/BTCUSDT");

    expect(() => initMiniApp({ navigate: vi.fn() })).not.toThrow();
    expect(app.ready).toHaveBeenCalledTimes(1);
  });
});

describe("outside Telegram", () => {
  it("throws nothing and changes nothing", () => {
    expect(() => initMiniApp({ navigate: vi.fn() })).not.toThrow();
    expect(document.documentElement.getAttribute("style")).toBeNull();
    expect(document.documentElement.dataset.scheme).toBeUndefined();
  });

  it("sends no authorization header, and calls fetch with the URL alone", async () => {
    const calls: unknown[][] = [];
    vi.stubGlobal("fetch", async (...args: unknown[]) => {
      calls.push(args);
      return new Response(JSON.stringify({ timeframes: [] }), { status: 200 });
    });

    await fetchTimeframes();

    expect(authorizationHeader()).toEqual({});
    expect(calls).toHaveLength(1);
    expect(calls[0]).toHaveLength(1);
    vi.unstubAllGlobals();
  });

  it("requests nothing from telegram.org", async () => {
    at("/chart/binance/BTCUSDT");

    await loadTelegramScript();

    expect(document.head.querySelector("script[src*='telegram.org']")).toBeNull();
    expect(launchedFromTelegram()).toBe(false);
  });
});

describe("how Telegram's script is loaded", () => {
  it("is added only when the address carries launch data, and only once", async () => {
    at("/#tgWebAppData=query_id%3DAAx&tgWebAppVersion=7.10");
    expect(launchedFromTelegram()).toBe(true);

    void loadTelegramScript({ timeoutMs: 10 });
    void loadTelegramScript({ timeoutMs: 10 });

    const tags = document.head.querySelectorAll("script[src*='telegram.org']");
    expect(tags).toHaveLength(1);
    expect(tags[0]?.getAttribute("src")).toBe("https://telegram.org/js/telegram-web-app.js");
  });

  it("gives up after its timeout and lets the page load as itself", async () => {
    at("/#tgWebAppData=x");

    await expect(loadTelegramScript({ timeoutMs: 5 })).resolves.toBeUndefined();
  });
});

describe("the launch data", () => {
  it("is Telegram's when there is Telegram", () => {
    install(standIn());

    expect(launchData()).toBe(LAUNCH);
  });

  it("is the development value only in development, and a test run is development", () => {
    vi.stubEnv("VITE_DEV_INITDATA", "dev-launch");

    expect(launchData()).toBe("dev-launch");
    vi.unstubAllEnvs();
  });
});
