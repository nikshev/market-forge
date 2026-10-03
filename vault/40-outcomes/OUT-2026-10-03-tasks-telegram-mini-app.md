---
id: OUT-2026-10-03-tasks-telegram-mini-app
step: tasks
records: [REQ-WP-080]
commit: null
---

## What was done

Broke the plan into 23 tasks in seven phases, then ran the analysis of `spec.md`, `plan.md` and
`tasks.md` against each other. Every FR and SC maps to at least one task (the coverage table is in
`tasks.md`). The analysis found three things; each was fixed before this commit.

## What was decided

**The analysis found, and what was done:**

- **The order contradicted itself.** T016 said to record the RED of the web tests "before T012/T014",
  and was numbered after them. A reader following the list in order would have implemented first.
  Each web test task now says to run it and record its RED where it is written; T016 is only the
  green afterwards, and the dependency paragraph says so.
- **The spec's older-client edge case had no test.** Telegram clients below the Bot API version that
  provides a method must not make the page throw; the stand-in tests only covered a *present*
  `disableVerticalSwipes`. T011 now also runs with the back button and the swipe call absent.
- **The dark theme had no automatic check at all.** The plan's own open item was whether the chart
  palette needs more than a prop; nothing would have shown a light chart on a dark page except a
  phone. T011 now asserts that `Chart` given a dark scheme hands the chart library a dark layout, and
  T023 leaves the rest to the phone, where it is named as a finding if wrong.

**Also decided.**

- **Status stays `tested` after the code is done.** SC-005 is "shown on a phone, from a bot" and needs
  the owner's bot token, a tunnel and a domain. Setting `implemented` before that would be the
  [[REQ-WP-076]] mistake again: a green suite and an unshown product.
- **The local deploy uses `--no-deps api web`** so `worker` and `resample` are not recreated and the
  24-hour measurement of [[REQ-WP-079]] is not disturbed.
- **Python tests carry the trace edges; vitest carries the page's acceptance.** The graph counts only
  pytest markers, so the verifier, the gate, the public-surface and the compose tests are Python and
  run in every commit; the page, the start parameter, the TypeScript signer and the build check run in
  CI and under `make web-test`, as [[ADR-021]] arranges.

## What is still open

- Whether the existing `Chart.test.tsx` mock of the chart library exposes the layout options it was
  given; if not, T011's dark-scheme assertion needs a small seam first.
- The bot token, the tunnel token and the domain, for T023 only.
