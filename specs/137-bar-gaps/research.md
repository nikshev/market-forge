# Research: marking a gap

## R1. What the library offers
Series markers (time, position, shape, colour, id, text) on any series type; no vertical-line primitive in 4.2.3.

## R2. Why not a time-true axis
The lower pane lines up with the chart by index ([[REQ-WP-092]]), and the visible range and the channel window are indices.
A time-true axis would stretch a 397-slot hole across the view and change every one of those rules.

## R3. Where a gap is known
From two consecutive bars' own windows: nothing else is needed, and nothing else can disagree.
