// @trace: REQ-WP-083
// @trace: REQ-WP-080
//
// The page as a Telegram Mini App.
//
// Everything here is a no-op outside Telegram: no script is requested, no header is sent, nothing is
// thrown. Inside it: tell Telegram the page is ready and expand it, follow its theme, use its own back
// button to get from a chart to the overview, and stop its vertical-swipe gesture from swallowing the
// touches meant for the chart (found the hard way by `lexa-reader`, which this follows).
//
// Telegram's script is loaded only when the address carries launch data. A static `<script>` tag would
// make every ordinary page load call out to telegram.org, which is a change in behaviour outside
// Telegram.

import { applyTelegramTheme, type Scheme } from "./theme";

interface BackButton {
  show: () => void;
  hide: () => void;
  onClick: (callback: () => void) => void;
  offClick: (callback: () => void) => void;
}

export interface TelegramWebApp {
  initData?: string;
  initDataUnsafe?: { start_param?: string };
  colorScheme?: Scheme;
  themeParams?: Record<string, string>;
  ready?: () => void;
  expand?: () => void;
  // Bot API 7.7 and later; an older client has none.
  disableVerticalSwipes?: () => void;
  BackButton?: BackButton;
  onEvent?: (event: string, callback: () => void) => void;
  offEvent?: (event: string, callback: () => void) => void;
}

const SCRIPT_URL = "https://telegram.org/js/telegram-web-app.js";
const DEFAULT_SCRIPT_TIMEOUT_MS = 3000;

export function webApp(): TelegramWebApp | undefined {
  return (window as unknown as { Telegram?: { WebApp?: TelegramWebApp } }).Telegram?.WebApp;
}

// A launch from Telegram carries its data in the address hash.
export function launchedFromTelegram(hash: string = window.location.hash): boolean {
  return hash.includes("tgWebAppData=");
}

export function loadTelegramScript(
  options: { timeoutMs?: number } = {},
): Promise<void> {
  if (!launchedFromTelegram() || webApp() !== undefined) {
    return Promise.resolve();
  }
  if (document.head.querySelector("script[data-telegram]") !== null) {
    return Promise.resolve();
  }
  return new Promise<void>((resolve) => {
    const tag = document.createElement("script");
    tag.src = SCRIPT_URL;
    tag.dataset.telegram = "true";
    // Whatever happens, the page loads: blocked, slow or absent, it simply runs as itself.
    const done = (): void => resolve();
    tag.onload = done;
    tag.onerror = done;
    document.head.appendChild(tag);
    setTimeout(done, options.timeoutMs ?? DEFAULT_SCRIPT_TIMEOUT_MS);
  });
}

// What a request sends to prove the launch. Telegram's own data inside Telegram; the development value
// only in development, and `import.meta.env.DEV` is false in a production build, so the build drops it.
export function launchData(): string {
  const fromTelegram = webApp()?.initData;
  if (fromTelegram) {
    return fromTelegram;
  }
  if (import.meta.env.DEV) {
    return import.meta.env.VITE_DEV_INITDATA ?? "";
  }
  return "";
}

export function authorizationHeader(): Record<string, string> {
  const data = launchData();
  return data === "" ? {} : { Authorization: `tma ${data}` };
}

const initialised = new WeakSet<object>();

function syncBackButton(app: TelegramWebApp, navigate: (path: string) => void): void {
  const button = app.BackButton;
  if (button === undefined) {
    return;
  }
  if (window.location.pathname.startsWith("/chart/")) {
    button.onClick(() => navigate("/"));
    button.show();
  } else {
    button.hide();
  }
}

export function initMiniApp(
  options: { navigate?: (path: string) => void } = {},
): void {
  const app = webApp();
  if (app === undefined || initialised.has(app)) {
    return;
  }
  initialised.add(app);
  const navigate = options.navigate ?? ((path: string) => window.location.assign(path));

  app.ready?.();
  app.expand?.();
  app.disableVerticalSwipes?.();
  applyTelegramTheme(app);
  syncBackButton(app, navigate);
}
