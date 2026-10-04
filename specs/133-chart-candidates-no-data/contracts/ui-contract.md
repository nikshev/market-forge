# UI contract: candidates off by default, "no data" panes

What a test (and a screen reader) may rely on.

## Candidate switch

- A `button` named **"Candidate extrema"** with `aria-pressed` `"false"` on every load and `"true"` after one
  press; a second press returns it to `"false"`.
- Present whether or not the API returned candidates.
- Not part of the link: no query parameter is read or written for it.

## Chart marks

- With the switch off the chart is handed only confirmed marks; on, confirmed plus the candidates the API
  returned that `extremumMarkers` already allows at the instant (AS-SEEN-THEN: observed at or before it).

## Pane row (`group` named "Pane")

- A pane with data: `button` named exactly its label (`CVD`, `OFI (1m)`, ...) with `aria-pressed`, as today.
- A pane without data (availability known): a **disabled** `button` whose name is its label followed by
  "no data" (`CVD no data`).
- Availability unknown (loading, or a failed pane load): every pane as today; none says "no data".
- No pane with data: none pressed, and a `status` named "Pane contents" reading **"No pane has data for this
  view"** (only when availability is known).
- The existing messages ("Could not load this pane: ...", the `empty`/`unavailable` notes) are unchanged for a
  selected pane.
