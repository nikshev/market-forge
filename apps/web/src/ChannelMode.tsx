// @trace: REQ-WP-009
//
// The label is not decoration. PRD section 27.5 calls the two views a critical
// feature because the difference between them "directly exposes repaint-like
// differences"; a reader who cannot tell which one they have will read a refit
// as evidence that the model saw what was coming.
//
// So the mode is always on screen, and the refit says in words what it is.

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
    <section aria-label="Channel mode">
      <strong>{mode}</strong>
      <p>{EXPLANATION[mode]}</p>
      <button type="button" onClick={() => onChange(other)}>
        Show {other}
      </button>
    </section>
  );
}
