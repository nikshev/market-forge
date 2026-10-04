---
id: OUT-2026-10-04-tasks-volume-pane
step: tasks
records: [REQ-WP-085]
commit: null
---

## What was done

16 tasks, tests first. One pass of `speckit-analyze` over spec, plan and tasks: no constitution conflict, all
eight functional requirements and four success criteria covered, one real gap and five small findings.

## What the analysis found, and how it was resolved

- **U1 (HIGH): "Volume is no data when there are no bars" was not guaranteed.** The plan took "known" from
  `pointsLoaded`, which becomes true only when the *feature* series answers. With no bars and no `at`, the
  load returns early, `pointsLoaded` stays false, `available` stays `null`, and Volume would have been a live
  button reading an empty note instead of "no data". And `state`, which starts at `"ok"`, cannot say "the bars
  have loaded". Resolved with a separate `barsLoaded` flag (true when `fetchBars` answers ok, including with
  none); FR-005, plan D4, the data model, T005, T008 and T009 now say so.
- **D1:** the spec referred to REQ-WP-086, which did not exist; it is now drafted (the gap requirement).
- **C1, C2:** a self-contradicting task title and a vague "add a case if it can drift" were made concrete.
- **C3, C4:** the time wording (a bar's volume is known at its close, plotted at its open) was made explicit;
  and it was recorded that with a deep link whose `at` is in the past the page shows every loaded bar, volume
  included, as it does for candles. Not changed here.

## What was decided

- The check on the comment above the pane list is a line-by-line read against `PANES` and PRD §27.3, recorded
  in the implement note: a comment cannot be asserted by a test without asserting its words.

## What is still open

- Same as the plan note.
