// @trace: REQ-WP-074
// @trace: REQ-WP-083
//
// The row of timeframe buttons. PRD section 27 does not name one; the sections
// that imply it are §5.1's set, §28.2's parameter, §27.1's link and §27.2/§27.3's
// controls -- see the requirement note.
//
// No state and no address here: the page owns the in-force token, so what is
// displayed and what is requested are one value (FR-013), and a component that
// remembered its own selection could disagree with the chart.
//
// Material toggle buttons (REQ-WP-083): each is still a button with `aria-pressed`, so nothing a reader of
// the page could rely on has changed. The row scrolls inside itself at phone width.

import Box from "@mui/material/Box";
import ToggleButton from "@mui/material/ToggleButton";
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup";

import type { TimeframeOption } from "./timeframes";

export function TimeframeControl({
  offered,
  selected,
  onSelect,
}: {
  offered: readonly TimeframeOption[];
  selected: string;
  onSelect: (token: string) => void;
}): JSX.Element {
  return (
    <Box component="section" aria-label="Timeframe" sx={{ overflowX: "auto", pb: 0.5 }}>
      <ToggleButtonGroup
        exclusive
        size="small"
        color="primary"
        value={selected}
        // Pressing the pressed one reports `null`: a timeframe is always in force, so it is ignored.
        onChange={(_, token: string | null) => {
          if (token !== null) {
            onSelect(token);
          }
        }}
      >
        {offered.map((option) => (
          <ToggleButton key={option.token} value={option.token}>
            {option.token}
          </ToggleButton>
        ))}
      </ToggleButtonGroup>
    </Box>
  );
}
