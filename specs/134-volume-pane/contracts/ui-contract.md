# UI contract: the volume pane

- The pane `group` named "Pane" starts with a `button` named **"Volume"** (`aria-pressed`); the other nine
  keep their names and order after it.
- Selected, the pane is an `img` named `volume over N point(s)` (N = final bars) drawn as one vertical bar per point.
- No final bars (availability known): a disabled button named "Volume no data".
- A feature-series failure shows "Could not load this pane: ..." only when a feature pane is selected; it never
  hides Volume and never marks it "no data".
- With bars and no feature data the page opens on Volume and shows no "No pane has data for this view".
