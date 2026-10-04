---
id: OUT-2026-10-04-spec-chart-candidates-no-data
step: spec
records: [REQ-WP-084]
commit: null
---

## What was decided

- **"Has data" is read from the series the page already loads**, through `paneSeries`, not from a new
  endpoint and not from a list in the page. Each loaded point carries every feature's value, so the answer was
  already in hand; a feature producer added later turns its pane live with no change here.
- **The candidate switch is a view option of the page, not a deep-link layer.** The requirement draft said a
  link could restore it; reading the code showed the link's `overlays` list is §27.2's vocabulary and an
  existing test rejects any other name. Adding one would break that rule or make old links unreadable, so the
  requirement's acceptance was amended in this step (its second bullet) and the switch is off on every load.
- **A failure and a load in progress never read as "no data"** (a failure is not an absence, REQ-WP-009 FR-016).
- **The page opens on the first pane with data**, and never overrides a choice that is still valid: opening on
  CVD, which has no readings, was the dead-button problem in another form.
- **"No data" is for the loaded view**, and the spec says so rather than implying all-time absence.

## What is still open

- The plan has to settle where the switch sits (next to the layer controls or the extrema legend) and the
  disabled-button wording; both are inside the contract.
- Whether to remember the switch across reloads is deliberately not done.
- The misleading "this alert did not record which layers were on" notice is a different requirement.
- The feature producer (CVD, OFI from trades; the rest need other sources) is separate work and will change
  how many panes read "no data".
