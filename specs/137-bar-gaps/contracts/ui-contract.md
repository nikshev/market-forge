# UI contract: gaps

- One marker per gap on the main chart at the first bar after it, text `N missing`; none for contiguous bars.
- A `status` named "Gaps in the bars" below the chart lists each gap (N and the UTC span), most recent first, at most five,
  then "and K more"; absent with no gaps.
- The Volume pane and the CVD run starts carry the same markers where a point exists.
- The axis and the visible range are unchanged.
