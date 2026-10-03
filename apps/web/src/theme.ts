// @trace: REQ-WP-080
//
// The colour scheme: Telegram's theme applied to the page, and the chart's layout for a scheme.
//
// Outside Telegram nothing here runs and `chartLayout("light")` is empty, so the chart is exactly what
// it was. `lightweight-charts` cannot draw in jsdom, so the decision -- what a scheme gets -- is a pure
// function and is what is tested, the way `buildSeries` is.

import { ColorType, type ChartOptions, type DeepPartial } from "lightweight-charts";

export type Scheme = "light" | "dark";

// Telegram's `themeParams` keys, and the CSS variable each becomes.
const VARIABLES: Record<string, string> = {
  bg_color: "--tg-bg",
  text_color: "--tg-text",
  hint_color: "--tg-hint",
  link_color: "--tg-link",
  button_color: "--tg-button",
  button_text_color: "--tg-button-text",
  secondary_bg_color: "--tg-secondary-bg",
};

export function schemeNow(): Scheme {
  return document.documentElement.dataset.scheme === "dark" ? "dark" : "light";
}

export function chartLayout(scheme: Scheme): DeepPartial<ChartOptions> {
  if (scheme === "light") {
    return {};
  }
  return {
    layout: { background: { type: ColorType.Solid, color: "#17212b" }, textColor: "#d1d4dc" },
    grid: { vertLines: { color: "#2b3945" }, horzLines: { color: "#2b3945" } },
  };
}

export function applyTelegramTheme(app: {
  colorScheme?: Scheme;
  themeParams?: Record<string, string>;
}): void {
  const root = document.documentElement;
  for (const [key, value] of Object.entries(app.themeParams ?? {})) {
    const variable = VARIABLES[key];
    if (variable !== undefined) {
      root.style.setProperty(variable, value);
    }
  }
  if (app.colorScheme !== undefined) {
    root.dataset.scheme = app.colorScheme;
    root.style.colorScheme = app.colorScheme;
  }
  if (root.style.getPropertyValue("--tg-bg") !== "") {
    document.body.style.background = "var(--tg-bg)";
    document.body.style.color = "var(--tg-text, inherit)";
  }
}
