---
id: OUT-2026-09-09-plan-deep-link-overlays
step: plan
records: [REQ-US-002]
commit: null
---

## What was done

One module each side, plus the range function in `series.ts`. 10 tasks.

## What was decided

- **`visibleRangeFor` went into `series.ts`**, for the reason that file exists:
  jsdom cannot lay out a container, so a component test would assert nothing
  about where the chart looked.
- **The twelve layer names are a wire contract**, duplicated in Python and
  TypeScript with a comment on each side saying so. Nothing enforces the pair,
  which [[ADR-045]] records as a gap.
- **The page test stubs the chart.** `lightweight-charts` cannot initialize in
  jsdom, and the assertions are about what the reader is told, which sits above
  the chart.

## What is still open

- Nothing from this step.
