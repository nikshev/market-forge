---
id: OUT-2026-09-23-plan-chart-timeframe-control
step: plan
records: [REQ-WP-074]
commit: null
---

## What was done

[[REQ-WP-074]] planned as `specs/119-chart-timeframe-control/`: `plan.md`,
`research.md`, `data-model.md`, `contracts/timeframes-api.md`,
`contracts/web.md`, `quickstart.md`. Constitution Check passed before Phase 0
and again after Phase 1; no violations to justify.

## What was decided

**The offered set is a read, and it carries durations, not just tokens.**
`GET /api/v1/timeframes` returns `{token, timeframe_ns}` plus the source. The
duration on the wire is the whole point: with only tokens the frontend would
need a `"4h" → 14400e9` table — the second list FR-002 forbids, with units. With
it, the link's token is matched against what the deployment reported and the
duration is used as given. There is no fallback table to disagree with.

**`1m` is always offered.** §5.1 names it first and the ingest daemon always
produces it; `CHANNELFLOW_TIMEFRAMES` names what *resampling* builds. The union
lives in one function, `offered()`, which the markets view can reuse.

**The API reads the same variable through the same parser as the resampler.**
`Settings.timeframes` comes from `parse_list(CHANNELFLOW_TIMEFRAMES)`, so an
unknown token or a calendar period refuses the API at startup exactly as it
refuses the resampler — loud in both processes rather than quiet in one. Unset
is valid and means the source alone.

**The address is edited in place, not rebuilt.** A helper writes exactly one key
on the current `URLSearchParams`; `at`, `signal`, `chain`, `pool` and the
overlays survive (FR-009). `replaceState`, not `pushState`: a back button that
steps through six timeframes is a worse interface than one that leaves the page.
The mode's key is **deleted** for AS-SEEN-THEN rather than written as `true` —
absence is the default ADR-020 already reads, and `true` would be noise in every
copied link.

**Refusal is a state of its own, not a `LoadState` kind.** It is about the
question the page was asked, not about a load that failed; it exists before any
request, and drawing the chart beside it would show the empty chart FR-011
reserves for a quiet market.

**Stale responses are dropped by sequence, not by `AbortController`.** An abort
would surface as a `failed` load for a request the reader deliberately
superseded; sequencing is the correctness rule, aborting would be an
optimisation.

## What was rejected, and why it matters

- **A timeframe constant in the frontend.** Passes every test written against
  the default configuration and disagrees silently on a deployment that changed
  one `.env` line — the precise defect WP-073's FR-002 removed.
- **Vite build-time configuration (`VITE_TIMEFRAMES`).** One image could not
  serve two configurations, and the set would live in a second variable that can
  drift from `CHANNELFLOW_TIMEFRAMES`.
- **Inferring the set by probing known tokens.** Turns a configuration question
  into a data question and breaks the moment configuration names something the
  probe list lacks.
- **Parsing tokens arithmetically in TypeScript.** It would re-implement the
  vocabulary — including the week's Monday origin and the calendar-period
  refusal — in a second language, where the two can drift.
- **Serving `default` from the API.** The default is a property of a link, not
  a deployment; serving it would be a second place it is written.
- **`pushState`.** Navigation semantics for a view setting.
- **Falling back to the default with a notice.** The chart would still be drawn
  at a timeframe nobody asked for, under a heading saying something else.

## What is still open

- **Presentation, deliberately.** Styling and component library are not settled
  by the requirement's Reference section; the control's markup can be replaced
  without reopening the spec.
- **The markets view's half of the set.** [[REQ-WP-075]] needs the same list to
  show current state per timeframe; `offered()` is reusable, and what that view
  does with it is its own plan.
- **Whether the API should expose the token→ns map for calculator-style
  consumers.** Not needed by this feature; a later consumer should say so with a
  requirement rather than widen this response on spec.
