# Contract — the pane decision

```
PANES: readonly { feature: string; label: string }[]
paneSeries(points, feature) -> { points, state, note }
```

## Guarantees

- only the named feature's values appear;
- a point with no value for it is absent from the series — never zero, never
  carried forward from the previous point;
- a value of zero appears;
- points are ordered by instant whatever order they arrived in;
- two points at one instant collapse to the last received;
- `empty`, `unavailable` and a caller's failure are three distinguishable
  outcomes, and the first two carry different words.

## Does not

Render, fetch, or decide how a gap looks. The component draws a polyline over
whatever points come back; a break in the line is the consequence rather than a
decision this module makes.
