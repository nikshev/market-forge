// @trace: REQ-WP-102
//
// Whether the chart is live or delayed, said where the reader looks (REQ-WP-102). A chart that is quietly fifteen minutes
// behind and does not say so is the failure this feed exists to remove; one that says "delayed" and why is the honest state
// of the same chart when the socket is down. Nothing is drawn for a timeframe that has no live feed.

import Chip from "@mui/material/Chip";

import type { LiveStatus } from "./live";

export const DELAYED_EXPLANATION =
  "The live feed is not connected. The chart reloads every minute and can be up to fifteen minutes behind the market.";
export const LIVE_EXPLANATION =
  "Candles after the last stored bar come from the live feed; the forming candle is not final and is never stored.";

export function LiveChip({ status }: { status: LiveStatus }): JSX.Element | null {
  if (status === "off") {
    return null;
  }
  const live = status === "live";
  return (
    <Chip
      role="status"
      aria-label="Live feed"
      size="small"
      color={live ? "success" : "warning"}
      variant={live ? "filled" : "outlined"}
      label={live ? "live" : "delayed"}
      title={live ? LIVE_EXPLANATION : DELAYED_EXPLANATION}
      sx={{ ml: 1, verticalAlign: "middle" }}
    />
  );
}
