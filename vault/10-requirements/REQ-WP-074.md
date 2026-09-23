---
id: REQ-WP-074
title: The timeframe is chosen on the chart, and the link keeps up
type: work-package
prd_ref: "§27.1, §27.2, §27.3, §5.1, §28.2"
prd_lines: "4390-4405, 4406-4422, 4423-4436, 289-313, 4475-4487"
phase: null
status: planned
depends_on: [REQ-WP-009, REQ-WP-073]
tags: [timeframes]
---

## Requirement

The chart carries a **timeframe control**. A reader opens `BTCUSDT` and moves
between 5m, 15m, 30m, 1h, 4h, 1d and 1w on the chart itself, the way every
trading chart works. Editing the address bar is not the interface.

### What the PRD gives, and what it does not

§27.1 defines the deep link, verbatim:

> ```text
> /chart/binance/BTCUSDT?tf=15m&at=2026-09-06T11:15:00Z&signal=<uuid>
> ```

§5.1 names the timeframes, §28.2 takes `timeframe` among the parameters of
`GET /api/v1/bars`, and §27.2 and §27.3 establish that this chart has
controls — "Toggle layers" for twelve overlays and "Selectable panes" for nine
lower panes.

**§27 does not name a timeframe selector.** This requirement is therefore
*derived* from those four sections rather than quoted from one, in the manner
`docs/superpowers/specs/2026-09-08-cross-venue-acceptance-design.md` records for
other derived criteria: the PRD gives a set of timeframes, a read that takes
one, a link that carries one, and a chart built from selectable controls. The
selector is what those four imply; it is not a sentence anybody can point at.

### The link is not the alternative — it is the initial value

`tf` in the URL must keep working. §27.1 is the link **every alert this system
sends** carries, and an alert that opened a chart at the wrong timeframe would
misrepresent the signal it was about. So:

- the link's `tf` is the timeframe the chart **opens** at;
- the control changes it afterwards;
- a link with no `tf` opens at the documented default.

### Two defects this replaces

**The timeframe is parsed and dropped.** `parseDeepLink` returns
`DeepLink.timeframe`; `apps/web/src/App.tsx` uses it once, in the heading, while
every request is built from `const timeframeNs = 15 * MINUTE_NS`. Measured on
the running stack, 2026-09-17: the one-minute series returns 133 bars and the
fifteen-minute request returns `{"bars":[]}`, so the chart renders `empty` — a
correct report of a question asked at the wrong timeframe.

**A control that changes the screen and not the link.** `apps/web/src/App.tsx`
contains no `history.replaceState` or `pushState` at all. `modeFromQuery` reads
`as_seen_then` from the query to initialise the mode, and `ChannelModeControl`
changes the mode — after which the URL still describes the state the reader
left. A copied link then reproduces something other than what was on screen.
The timeframe control must not repeat this, and fixing the mode control's half
is in scope here because the mechanism is one mechanism.

## Acceptance

- The chart shows a timeframe control offering the configured set
  ([[REQ-WP-073]]), and choosing one re-reads bars, channel, features and
  extrema at that timeframe.
- The control's options come from configuration, not from a list written into
  the frontend. FR-002 of [[REQ-WP-073]] forbids a second list that can disagree
  with the first; this requirement is where the frontend's half of that is
  settled, including whatever API surface it needs.
- A link carrying `tf` opens at that timeframe. A link with none opens at the
  documented default, and that default is written in one place.
- Every request the chart issues carries the timeframe in force — proven by a
  test that asserts the timeframe **that reached the request**, for at least two
  values, so a constant cannot pass it.
- Changing the timeframe updates the address so that copying it reproduces the
  chart on screen. Proven by changing the control and comparing the link against
  a freshly opened one.
- The same holds for the channel mode: after toggling, the address describes
  what is displayed.
- The displayed timeframe and the requested timeframe agree by construction — a
  test opening a non-default `tf` finds one value, not two.
- An unsupported or unparseable `tf` is refused visibly, naming the timeframe
  that could not be honoured, rather than silently falling back. A silent
  fallback shows one timeframe's candles under another's name.
- A timeframe with no data reads as empty, not as failed. The distinction is
  [FR-016]'s and already correct in the code: a failed load must never be drawn
  as an empty chart, and an empty series must not claim to be a failure.

## Reference

The shape asked for, 2026-09-17, is investing.com's chart toolbar
(`https://www.investing.com/indices/us-30-futures`): a row of timeframe buttons
above the chart, a heading carrying the last price with its absolute and
percentage change, and the chart below.

**Taken from it**: the timeframe row as the primary control, and the price and
change heading, which is computed from bars this system already has.

**Not taken, and why:**

| element | why not |
|---|---|
| **Buy / Sell** | Constitution Principle IX: "Phases 1-3 form signals and alerts only. The system does not open positions." On that site these are broker links; here such a button would claim something untrue. |
| `5H` | Not a timeframe this system has. Its neighbour here is `4h`. |
| `1M` | A calendar month has no `timeframe_ns` — see [[REQ-WP-073]], where it is refused with a reason rather than approximated. The reference shows the button; this system will not have it until calendar periods have a key. |
| period-return row (`1 Day`, `1 Week`, … `Max`) | Returns over periods, not timeframes. Computable from bars, computed by nothing today; a separate requirement, not this one. |
| line/candle toggle | §27.2 names `candles` among twelve toggleable layers and names no line mode. |
| **Compare** | Overlaying another instrument is §17's cross-venue work. |
| **Analyze chart** (AI) | Out of scope entirely. |

**This section describes behaviour, not presentation.** Nothing here settles how
the control is styled or what component library draws it; that decision was
deliberately postponed on 2026-09-17 and can be taken after this requirement is
implemented, without reopening it.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-119-chart-timeframe-control]]
- **Outcomes:** [[OUT-2026-09-23-plan-chart-timeframe-control]], [[OUT-2026-09-23-spec-chart-timeframe-control]], [[OUT-2026-09-23-tasks-chart-timeframe-control]]
<!-- trace:end -->

## Notes

Human territory. Never machine-rewritten.
