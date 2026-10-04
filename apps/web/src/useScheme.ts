// @trace: REQ-WP-083
//
// Where the colour scheme comes from: Telegram's inside Telegram, the browser's outside it. Telegram wins
// when it is there, because the user chose that theme for Telegram and a Mini App is a guest in it.

import useMediaQuery from "@mui/material/useMediaQuery";
import { useEffect, useReducer } from "react";

import { webApp } from "./telegram";
import type { Scheme } from "./theme";

export function useScheme(): Scheme {
  // `noSsr`: read the browser's preference on the first render. The default reads it after, and a dark user
  // would see a flash of the light theme on every load.
  const prefersDark = useMediaQuery("(prefers-color-scheme: dark)", { noSsr: true });
  const [, refresh] = useReducer((count: number) => count + 1, 0);

  useEffect(() => {
    const app = webApp();
    if (app?.onEvent === undefined) {
      return undefined;
    }
    app.onEvent("themeChanged", refresh);
    return () => app.offEvent?.("themeChanged", refresh);
  }, []);

  const fromTelegram = webApp()?.colorScheme;
  if (fromTelegram === "light" || fromTelegram === "dark") {
    return fromTelegram;
  }
  return prefersDark ? "dark" : "light";
}
