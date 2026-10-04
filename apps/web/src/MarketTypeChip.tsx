// @trace: REQ-WP-083
//
// The market type as a chip whose colour tells spot from perp at a glance. The type was the thing this
// deployment first got wrong (Binance's feed is spot, not perp -- REQ-WP-081), so it is the one fact on the
// overview that is coloured.

import Chip from "@mui/material/Chip";

const COLOUR: Record<string, "info" | "warning"> = { spot: "info", perp: "warning" };

export function MarketTypeChip({ type }: { type: string }): JSX.Element {
  // A type nobody has coloured is shown plain, never in a colour that claims it is spot or perp.
  return <Chip size="small" label={type} color={COLOUR[type] ?? "default"} />;
}
