---
id: OUT-2026-09-10-implement-flow-panes
step: implement
records: [REQ-WP-027, REQ-PHASE-2]
commit: null
---

## What was done

`panes.ts`, `FlowPane.tsx`, `fetchFeatureSeries`, and the page holding a
selection. 19 new frontend tests, 63 in the web suite, typecheck and build clean,
9 of 9 mutants caught.

[[REQ-PHASE-2]]'s last unbuilt deliverable is closed and the phase reaches
`implemented` — **the fifth**, after Phase 6, Phase 0, Phase 1 and Phase 7.

## What the work found

- **Two existing tests were passing for a reason that was about to stop being
  true.** They asked for "the status" on the page and asserted about the
  overlay-restoration notice; being the *only* status was what made that
  unambiguous. A second status broke them. Both are now named — "Overlay
  restoration", "Pane contents", "Pane load" — and the tests ask by name, which
  is what they always meant and could not say. The accessible names are also
  better for a screen reader, which is the part that makes this a fix rather
  than a test repair.
- **The design question I nearly asked the user was already answered.** PRD
  §27.3 lists the nine panes outright. Deferring to the user without checking the
  document first would have cost a round trip and produced a worse answer.

## What the mutation sweep found

9 mutants over the decision module, 9 caught, including both halves of the rule
this feature exists for: drawing a missing value as zero, and dropping a real
zero along with the gaps.

## What is still open

- **I cannot see it.** Every criterion is checkable by a test, deliberately, but
  whether the pane reads well on a screen is not something this session can
  verify. A break in the line is how a gap appears; a reviewer may want it
  marked.
- **The selection is not persisted.** A reload forgets which pane was open. The
  deep link carries overlays and says nothing about panes, and adding it changes
  a format other things parse.
- **Six of PRD §27.3's nine panes are still unbuilt**, by scope rather than by
  omission: OI, funding, basis and liquidations are Phase 3's deliverable, and
  the DEX pair is Phase 4's.
