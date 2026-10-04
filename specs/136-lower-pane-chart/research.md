# Research: the lower pane as a chart

## R1. What the library can do (4.2.3, read from the installed typings)
`setCrosshairPosition`, `clearCrosshairPosition`, `subscribeCrosshairMove`, `subscribeVisibleLogicalRangeChange`,
`setVisibleLogicalRange`, price scale `minimumWidth`, histogram and line series, whitespace data, series `title`. No panes.

## R2. How two charts line up
The time axis is an index over the union of the series' times. Equal sequences of times give equal logical indices; a
bar with no value must be whitespace, and a series that holds only some times needs a backbone that holds them all.

## R3. Where values belong
A value's instant may be inside a bar. It is shown at the bar that contains it (the later wins), never at a slot of its own.

## R4. Fallback
In jsdom the library cannot lay out; the SVG stays for a missing handle and for the tests that read it.
