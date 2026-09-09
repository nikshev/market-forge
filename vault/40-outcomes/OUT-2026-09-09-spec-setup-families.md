---
id: OUT-2026-09-09-spec-setup-families
step: spec
records: [REQ-US-005]
commit: null
---

## What was done

`specs/029-setup-families/spec.md`: two user stories, 10 functional
requirements, 7 success criteria.

## What was decided

- **The restriction is on what may open, not on what is reported.** The engine
  holds one candidate at a time, so filtering afterwards leaves each family's
  count depending on the other family's setups.
- **A family does not touch a live candidate** (FR-003). Abandoning one
  mid-lifecycle would report an invalidation the engine never made.
- **Three of §31's fields are deliberately absent**, and the spec says which and
  why. Fields nothing reads describe behaviour that does not exist.

## What is still open

- **PRD §38's `channelflow backtest --strategy` CLI is unbuilt**, and no
  requirement covers it. This is the capability that command would call.
