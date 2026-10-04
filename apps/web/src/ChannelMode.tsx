// @trace: REQ-WP-009
// @trace: REQ-WP-083
//
// The label is not decoration. PRD section 27.5 calls the two views a critical
// feature because the difference between them "directly exposes repaint-like
// differences"; a reader who cannot tell which one they have will read a refit
// as evidence that the model saw what was coming.
//
// So the mode is always on screen, and the refit says in words what it is.

import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";

import { AS_SEEN_THEN, CURRENT_REFIT } from "./types";
import type { ChannelMode } from "./types";

const EXPLANATION: Record<ChannelMode, string> = {
  [AS_SEEN_THEN]: "the channel snapshot stored at this moment, unchanged since",
  [CURRENT_REFIT]: "refitted now over current history — it has seen what followed",
};

export function ChannelModeControl({
  mode,
  onChange,
}: {
  mode: ChannelMode;
  onChange: (mode: ChannelMode) => void;
}): JSX.Element {
  const other = mode === AS_SEEN_THEN ? CURRENT_REFIT : AS_SEEN_THEN;
  return (
    <Paper
      component="section"
      aria-label="Channel mode"
      variant="outlined"
      sx={{ p: 1.5, display: "flex", flexWrap: "wrap", alignItems: "center", gap: 1.5 }}
    >
      {/* The two chips must not look alike: a reader who cannot tell which view they have will read a
          refit as evidence the model saw what was coming (PRD 27.5). */}
      <Chip
        label={mode}
        color={mode === AS_SEEN_THEN ? "primary" : "warning"}
        sx={{ fontWeight: 700 }}
      />
      <Typography variant="body2" color="text.secondary" sx={{ flex: "1 1 220px" }}>
        {EXPLANATION[mode]}
      </Typography>
      <Button variant="outlined" size="small" onClick={() => onChange(other)}>
        Show {other}
      </Button>
    </Paper>
  );
}
