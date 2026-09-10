# Contract — the stop-path view

```ts
stopPath({ position, proposals, excursion, mode, atNs }) -> StopPathView
```

There is deliberately no `bars` parameter.

## Guarantees

- Every path point comes from a supplied proposal. The same position and
  proposals produce the same path regardless of what the market did next.
- In `AS_SEEN_THEN`, no proposal later than `atNs` appears. In `CURRENT REFIT`
  the filter is absent, for the reason [[REQ-WP-028]] gives: §27.5 makes that
  mode where repaint-like differences are meant to be visible.
- Movements, holds and refusals are three kinds, and holds keep their own
  reasons, so two holds with different causes are two different points.
- Reason codes are carried verbatim, including ones the view does not
  recognise. A dropped reason is a veto that looks like no veto.
- An absent hard stop yields no hard-stop level. An absent anchor yields no
  anchor.
- A proposal whose anchor became knowable after the proposal was made yields
  `inconsistent` and no path, naming the proposal.
- Excursion is `null` when nothing was observed; locked profit is `0` when the
  stop is still on the losing side of entry.

## Does not

Compute the trail, decide colours, or lay anything out. It does not know what a
chart is.
