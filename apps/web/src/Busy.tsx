// @trace: REQ-WP-103
//
// A page that is waiting says so (REQ-WP-103). An empty area looked the same whether the page was still fetching or had broken,
// and the owner could not tell a slow load from a bug. Every place the page waits shows this, with a name -- and takes it away
// when the answer arrives, whatever the answer is (data, nothing, or a failure, each of which the page already states).
//
// A `progressbar`, never a `status`: the page's statements about the data are `status` and `alert`, and a spinner must neither
// hide nor imitate one.

import Box from "@mui/material/Box";
import CircularProgress from "@mui/material/CircularProgress";
import Typography from "@mui/material/Typography";

export function Busy({
  label,
  inline = false,
}: {
  /** What is being waited for, "Loading the pane": the spinner's accessible name, and its caption unless inline. */
  label: string;
  /** Small, in a line of text, with no caption of its own. */
  inline?: boolean;
}): JSX.Element {
  if (inline) {
    return (
      <CircularProgress
        aria-label={label}
        size={14}
        thickness={5}
        sx={{ verticalAlign: "middle", ml: 1 }}
      />
    );
  }
  return (
    <Box sx={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 1, py: 3 }}>
      <CircularProgress aria-label={label} size={28} />
      <Typography variant="caption" color="text.secondary" aria-hidden>
        {label}
      </Typography>
    </Box>
  );
}
