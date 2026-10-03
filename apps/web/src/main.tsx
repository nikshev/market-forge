// @trace: REQ-WP-001
// @trace: REQ-WP-080
import React from "react";
import ReactDOM from "react-dom/client";

import { App } from "./App";
import { applyStartParam, startParamFromLaunch } from "./startParam";
import { initMiniApp, launchedFromTelegram, loadTelegramScript } from "./telegram";

const root = document.getElementById("root");
if (!root) {
  throw new Error("root element missing from index.html");
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
      <App />
    </React.StrictMode>,
  );
}

void boot(root);
