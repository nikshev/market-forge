---
id: OUT-2026-10-03-spec-no-unfinalized-upsample
step: spec
records: [REQ-NRT-UPSAMPLE]
commit: null
---

## What was done

Specified [[REQ-NRT-UPSAMPLE]] as `specs/125-no-unfinalized-upsample/spec.md`: four stories, eight
requirements. Before writing it the resampler was read and **run**: `resample` was handed three
five-minute windows (`specs/125-no-unfinalized-upsample/probe.py`). A complete one gave a bar, as it
should; a window of minutes 0,1,2,3,3 — minute 4 missing — **also gave a bar**; and a complete
window with one non-final source bar **also gave a bar**. Live, the `bars` table has 55,546
one-minute rows with 55,546 distinct keys, so neither case has occurred on the deployment.

## What was decided

- **The requirement is stated as a property of the read path.** It speaks of "a consumer", and no
  component consumes two timeframes in one computation: the extrema hierarchy and confluence
  features of §13A.17 have no note and no code. A guarantee on the as-of read binds a consumer
  written later; a test of a consumer that does not exist would bind nothing.
- **The two holes are in scope although latent.** Nothing on the deployment triggers them, but
  `resample`'s contract is weaker than the sentence it is cited for, and what keeps them out is
  another module's behaviour (`bars` refuses unfinalized rows on write; the table happens to hold no
  duplicate). `read_bars` does not deduplicate, so one duplicate row would reach `resample` as it is.
- **Completeness means identity, not count.** FR-001 asks for each source minute exactly once and
  final, because a count satisfied by the wrong minutes is the failure the requirement names.
- **The hard gate is met by User Story 4.** R5 needs a linked test; "a test that has never seen the
  violation" is the requirement's own phrase for what is not enough, so the mutation sweep is a
  story and not an afterthought.

## What is still open

- Where the as-of read is implemented for the series (`read_bars(as_of_ns=…)` over the table) and
  whether the API's own `/bars` honours the same: the plan must read both before the tasks say what
  a test of FR-004/FR-005 drives.
- Whether a refusal's new reasons (duplicated, not final) fit the existing `Refusal` shape or want a
  field: planning decides.
- `1M` and the extrema hierarchy remain with no note, as before.
