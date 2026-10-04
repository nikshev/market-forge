// @trace: REQ-WP-084
//
// Candidate extrema are the detector's unconfirmed turns: it may still invalidate them, there are many, and
// they sit on the price. They are drawn only when the reader asks, so the first view of a chart is the
// confirmed structure. This is a view option of the page, not one of PRD section 27.2's layers: the deep
// link's layer list is that section's vocabulary and nothing else, so the link neither sets nor clears it.

import ToggleButton from "@mui/material/ToggleButton";

export function CandidateSwitch({
  pressed,
  onChange,
}: {
  pressed: boolean;
  onChange: (next: boolean) => void;
}): JSX.Element {
  return (
    <ToggleButton
      value="candidates"
      size="small"
      color="primary"
      selected={pressed}
      onChange={() => onChange(!pressed)}
      sx={{ alignSelf: "flex-start" }}
    >
      Candidate extrema
    </ToggleButton>
  );
}
