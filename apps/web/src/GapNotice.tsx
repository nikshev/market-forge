// @trace: REQ-WP-086
//
// The gaps among the loaded bars, in words (the marker on the chart says how many; only words can say over what span, and a
// screen reader gets the same facts). Absent when there is no gap. Capped at five lines with the rest counted: a series can
// carry hundreds.

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { useMemo } from "react";

import { findGaps, noticeLines, NOTICE_LIMIT } from "./gaps";
import type { BarOut } from "./types";

export function GapNotice({ bars }: { bars: readonly BarOut[] }): JSX.Element | null {
  const lines = useMemo(() => noticeLines(findGaps(bars)), [bars]);
  if (lines.length === 0) {
    return null;
  }
  const listed = lines.slice(0, NOTICE_LIMIT);
  const more = lines.slice(NOTICE_LIMIT);

  return (
    <Alert severity="warning" variant="outlined" role="status" aria-label="Gaps in the bars" sx={{ my: 1 }}>
      <Typography variant="body2" sx={{ fontWeight: 700 }}>
        Bars missing from this series
      </Typography>
      <Box component="ul" sx={{ m: 0, pl: 2.5 }}>
        {listed.map((line) => (
          <li key={line}>{line}</li>
        ))}
      </Box>
      {more.map((line) => (
        <Typography key={line} variant="body2">
          {line}
        </Typography>
      ))}
    </Alert>
  );
}
