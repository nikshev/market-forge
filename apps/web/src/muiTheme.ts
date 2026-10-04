// @trace: REQ-WP-083
//
// The one theme (REQ-WP-083): a pure function of the colour scheme and, inside Telegram, of Telegram's own
// theme parameters. Nothing else in the interface picks a colour: a palette changed here changes everywhere,
// and the chart canvas, which is not Material, takes its colours from this theme too (`chartLayout`).
//
// The brand is the logo's: a violet channel (#7c5cff) with an amber point on a near-black ground. It is the
// primary colour when Telegram supplies none; where Telegram supplies a colour, Telegram's wins, because a
// Mini App that ignores its host's theme looks like a web page pasted into a chat.

import { createTheme, type Theme } from "@mui/material/styles";

import type { Scheme } from "./theme";

// The subset of Telegram's `themeParams` the interface uses.
export interface TelegramThemeParams {
  bg_color?: string;
  secondary_bg_color?: string;
  text_color?: string;
  hint_color?: string;
  button_color?: string;
  button_text_color?: string;
}

const BRAND = { violet: "#7c5cff", amber: "#ffb02e" } as const;

// The theme's own colours, used wherever Telegram supplies none. Chosen so that text meets a contrast of 4.5
// on both surfaces, which `muiTheme.test.ts` computes rather than assumes.
const OWN = {
  light: { page: "#f4f4f8", paper: "#ffffff", text: "#17171c", hint: "#5b5b66" },
  dark: { page: "#141417", paper: "#1c1c21", text: "#ececf1", hint: "#a3a3b0" },
} as const;

const HEX = /^#(?:[0-9a-f]{3}|[0-9a-f]{6}|[0-9a-f]{8})$/i;

// A colour, or the fallback. Telegram's values reach a stylesheet; one that is not a plain hex colour
// (`url(...)`, `red; x`) is not put there.
function pick(value: string | undefined, fallback: string): string {
  return value !== undefined && HEX.test(value) ? value : fallback;
}

export function buildTheme(scheme: Scheme, telegram: TelegramThemeParams = {}): Theme {
  const own = OWN[scheme];
  const paper = pick(telegram.bg_color, own.paper);
  return createTheme({
    palette: {
      mode: scheme,
      primary: {
        main: pick(telegram.button_color, BRAND.violet),
        contrastText: pick(telegram.button_text_color, "#ffffff"),
      },
      secondary: { main: BRAND.amber },
      background: { default: pick(telegram.secondary_bg_color, own.page), paper },
      text: {
        primary: pick(telegram.text_color, own.text),
        secondary: pick(telegram.hint_color, own.hint),
      },
    },
    shape: { borderRadius: 12 },
    typography: {
      fontFamily:
        '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
      h6: { fontWeight: 700 },
      button: { textTransform: "none", fontWeight: 600 },
    },
    components: {
      MuiCard: { defaultProps: { variant: "outlined" } },
      MuiPaper: { styleOverrides: { root: { backgroundImage: "none" } } },
      MuiToggleButton: { styleOverrides: { root: { textTransform: "none", whiteSpace: "nowrap" } } },
    },
  });
}

function channel(value: number): number {
  const v = value / 255;
  return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4;
}

function luminance(hex: string): number {
  let h = hex.replace("#", "");
  if (h.length === 3) {
    h = [...h].map((c) => c + c).join("");
  }
  const [r, g, b] = [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16));
  return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b);
}

// WCAG's contrast ratio of two hex colours: 1 (none) to 21 (black on white).
export function contrastRatio(a: string, b: string): number {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
}
