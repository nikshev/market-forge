// @trace: REQ-WP-089
// @trace: REQ-WP-103
//
// The volume profile's own controls: which window it covers, and a line saying what it covers. A profile built from
// three hours of blocks says "covers 3 h 20 m of 24 h" rather than reading as a 24-hour profile; a market with no
// collected bins says so, and a failed load says it failed. None of them is drawn as an empty profile.

import Box from "@mui/material/Box";
import ToggleButton from "@mui/material/ToggleButton";
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup";
import Typography from "@mui/material/Typography";

import { Busy } from "./Busy";
import { coverageLine } from "./profileView";
import { PROFILE_WINDOWS } from "./profileWindows";
import type { ProfileWindow } from "./profileWindows";
import type { VolumeProfileOut } from "./types";

export type ProfileState = "loading" | "ok" | "none" | "failed";

export function ProfileControls({
  window,
  onWindow,
  profile,
  state,
  failure = "",
}: {
  window: ProfileWindow;
  onWindow: (window: ProfileWindow) => void;
  profile: VolumeProfileOut | null;
  state: ProfileState;
  failure?: string;
}): JSX.Element {
  let line = "";
  if (state === "ok" && profile !== null) {
    line = coverageLine(profile);
  } else if (state === "none") {
    line = "no price bins collected for this market yet";
  } else if (state === "failed") {
    line = `Could not load the profile: ${failure}`;
  }
  return (
    <Box sx={{ display: "flex", alignItems: "center", gap: 2, flexWrap: "wrap", my: 1 }}>
      <ToggleButtonGroup
        exclusive
        size="small"
        color="primary"
        aria-label="Profile window"
        value={window}
        // Pressing the pressed one reports `null`: a window is always in force, so it is ignored.
        onChange={(_, next: ProfileWindow | null) => {
          if (next !== null) {
            onWindow(next);
          }
        }}
      >
        {PROFILE_WINDOWS.map((option) => (
          // Named apart from the timeframe buttons, which offer the same words: two buttons of one name on a page cannot be
          // told apart by a screen reader or a test, and they mean different things.
          <ToggleButton key={option} value={option} aria-label={`${option} profile`}>
            {option}
          </ToggleButton>
        ))}
      </ToggleButtonGroup>
      {state === "loading" ? <Busy label="Loading the volume profile" inline /> : null}
      <Typography variant="body2" color="text.secondary" role="status" aria-label="Volume profile">
        {line}
      </Typography>
    </Box>
  );
}
