---
id: OUT-2026-09-10-spec-derivatives-panes
step: spec
records: [REQ-WP-030]
commit: null
---

## What was done

`specs/068-derivatives-panes/spec.md`: three user stories, 7 functional
requirements, 5 success criteria. [[REQ-WP-030]] moves to `specified`.

## What was decided

- **The check must read the real pane list.** A check against a copy would pass
  forever and prove nothing, and copying the names into the test is the obvious
  way to write it — which is why FR-003 exists rather than being left implied.
- **The check crosses languages.** Panes are TypeScript, the registry is Python.
  Either side alone compares a list against itself.
- **A registered-but-unrecorded feature is named as a known limitation.** It
  renders "no readings of this feature", which is honest and will read as a bug
  to whoever opens it first. Saying so is the difference between a limitation and
  a surprise.
- **SC-001 names a number, deliberately**, where the previous pane spec refused
  to. That one asserted a property that must survive the tenth pane; this one is
  checking that four specific panes arrived.

## What is still open

- **Nothing writes derivative features into the feature table.** The gap belongs
  to whoever wires the derivatives path; this work names it and does not depend
  on it.
