# UI contract: the lower pane chart

- The pane's chart is an element with `role="img"` named `<feature> over N point(s)` (as the SVG was).
- Inside it: a legend with the pane's title and last value; a labelled value axis; for CVD a zero line.
- Roles and names of the pane group, the buttons, the "no data" buttons and the status messages: unchanged.
- Without a handle to the main chart: the SVG, exactly as before.
- Zooming or panning either chart moves both; the crosshair is shared; a new pane chart starts at the main chart's range.
- The main chart holds the whole bar sequence whatever layers are on.
