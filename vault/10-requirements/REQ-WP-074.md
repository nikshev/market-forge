---
id: REQ-WP-074
title: The deep link's timeframe reaches the read
type: work-package
prd_ref: "§27.1, §28.2"
prd_lines: "4390-4405, 4475-4487"
phase: null
status: draft
depends_on: [REQ-WP-009, REQ-WP-073]
tags: [timeframes]
---

## Requirement

§27.1 gives the deep link, verbatim:

> ```text
> /chart/binance/BTCUSDT?tf=15m&at=2026-09-06T11:15:00Z&signal=<uuid>
> ```

`tf` is a parameter of the route, and §28.2 takes `timeframe` among the
parameters of `GET /api/v1/bars`. The link's timeframe must therefore reach the
request. Today it does not.

### The parameter is parsed and then dropped

`parseDeepLink` reads `tf` and returns it as `DeepLink.timeframe`
(`apps/web/src/deepLink.ts`), with a default of `15m`. In `apps/web/src/App.tsx`
the value is used **once** — in the heading, `{link.symbol} · {link.venue} ·
{link.timeframe}` — while every one of the four requests is built from a
constant:

```ts
const timeframeNs = 15 * MINUTE_NS;
```

So the page states one timeframe and asks for another whenever the two differ.
Nothing in the file marks this as a decision; in a codebase that comments its
compromises, the absence of a comment is itself evidence that the wiring was
missed rather than declined.

**Measured on a running stack**, 2026-09-17: with the ingest daemon writing
one-minute bars, `GET /api/v1/bars` at `timeframe_ns=60000000000` returns a
series and the same request at `900000000000` returns `{"bars":[]}` — so the
chart asks for the empty one and reports a failed load, on a deployment whose
data is fine.

No test catches it: `deepLinkOverlays.test.tsx` asserts that the parser returns
`tf=15m`, and nothing asserts which timeframe the request carried.

## Acceptance

- Every request the chart issues — bars, channel, features, extrema — carries the
  timeframe named by the link, not a constant.
- A link with no `tf` uses the documented default, and the default is written in
  one place rather than repeated per request.
- A test asserts the timeframe **that reached the request**, for at least two
  different `tf` values, so a future constant cannot pass it.
- The heading and the request agree by construction: a test opening a link at a
  non-default `tf` finds the same value displayed and requested.
- An unparseable or unsupported `tf` is refused visibly — the page says which
  timeframe it could not honour — rather than silently falling back to the
  default. A silent fallback shows a chart of one timeframe under the name of
  another.

## Trace

<!-- trace:begin -->
_No linked artifacts yet._
<!-- trace:end -->

## Notes

Human territory. Never machine-rewritten.
