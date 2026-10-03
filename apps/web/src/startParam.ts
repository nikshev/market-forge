// @trace: REQ-WP-080
//
// A Mini App link carries the chart state in `start_param`, which Telegram limits to letters, digits,
// `_` and `-`, at most 512 characters. PRD US-002 -- "press a button in Telegram and open the chart at
// the signal's timestamp" -- is the reason: the alert's button must land where the query-string deep link
// does.
//
// The encoding is the base64url of the deep link's path and query, and nothing cleverer: a custom compact
// form would be a second format to keep in step with `deepLink.ts`, which already reads the query form.
//
// The decoded value replaces the address, so it is matched against a strict pattern first. Anything that
// is not the overview or `/chart/<venue>/<symbol>` with an optional query opens the overview.

import { webApp } from "./telegram";

const TELEGRAM_ALPHABET = /^[A-Za-z0-9_-]{1,512}$/;
const ALLOWED_TARGET =
  /^\/(?:chart\/[A-Za-z0-9][A-Za-z0-9._-]*\/[A-Za-z0-9][A-Za-z0-9._-]*)?(?:\?[A-Za-z0-9_.~%=&:+,-]*)?$/;

export function encodeStartParam(pathAndQuery: string): string {
  const bytes = new TextEncoder().encode(pathAndQuery);
  let binary = "";
  for (const byte of bytes) {
    binary += String.fromCharCode(byte);
  }
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

export function decodeStartParam(raw: string): string | null {
  if (!TELEGRAM_ALPHABET.test(raw)) {
    return null;
  }
  try {
    const padded = raw.replace(/-/g, "+").replace(/_/g, "/").padEnd(Math.ceil(raw.length / 4) * 4, "=");
    const binary = atob(padded);
    const bytes = Uint8Array.from(binary, (char) => char.charCodeAt(0));
    const decoded = new TextDecoder("utf-8", { fatal: true }).decode(bytes);
    return ALLOWED_TARGET.test(decoded) ? decoded : null;
  } catch {
    return null;
  }
}

// What Telegram handed the page: the SDK's own field, or the address hash it launched with.
export function startParamFromLaunch(): string | null {
  const fromSdk = webApp()?.initDataUnsafe?.start_param;
  if (fromSdk) {
    return fromSdk;
  }
  return new URLSearchParams(window.location.hash.replace(/^#/, "")).get("tgWebAppStartParam");
}

// Put the state in the address before the page reads it. A page that was opened at a chart already says
// where it is, and is left alone.
export function applyStartParam(raw: string | null): void {
  if (raw === null || window.location.pathname !== "/" || window.location.search !== "") {
    return;
  }
  const target = decodeStartParam(raw);
  if (target !== null) {
    window.history.replaceState(null, "", target);
  }
}
