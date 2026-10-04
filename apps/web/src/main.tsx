// @trace: REQ-WP-001
// @trace: REQ-WP-080
// @trace: REQ-WP-083
import CssBaseline from "@mui/material/CssBaseline";
import { ThemeProvider } from "@mui/material/styles";
import React, { useMemo } from "react";
import ReactDOM from "react-dom/client";

import { App } from "./App";
import { buildTheme, type TelegramThemeParams } from "./muiTheme";
import { applyStartParam, startParamFromLaunch } from "./startParam";
import { initMiniApp, launchedFromTelegram, loadTelegramScript, webApp } from "./telegram";
import { useScheme } from "./useScheme";

const root = document.getElementById("root");
if (!root) {
  throw new Error("root element missing from index.html");
}

// One theme for the whole interface, from the scheme (Telegram's inside Telegram, the browser's outside) and,
// inside Telegram, Telegram's own colours (REQ-WP-083).
function Themed(): JSX.Element {
  const scheme = useScheme();
  const params = (webApp()?.themeParams ?? {}) as TelegramThemeParams;
  const key = JSON.stringify(params);
  // `key` stands for the parameters: a new object each render would rebuild the theme every time.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const theme = useMemo(() => buildTheme(scheme, params), [scheme, key]);
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <App />
    </ThemeProvider>
  );
}

// Inside Telegram: load its script, tell it the page is ready, and put a link's chart state in the
// address *before* the page reads the address. Outside it, none of this does anything.
async function boot(container: HTMLElement): Promise<void> {
  if (launchedFromTelegram()) {
    await loadTelegramScript();
  }
  initMiniApp();
  applyStartParam(startParamFromLaunch());
  ReactDOM.createRoot(container).render(
    <React.StrictMode>
      <Themed />
    </React.StrictMode>,
  );
}

void boot(root);
