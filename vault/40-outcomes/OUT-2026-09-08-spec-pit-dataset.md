---
id: OUT-2026-09-08-spec-pit-dataset
step: spec
records: [REQ-WP-017, REQ-BIAS-001, REQ-BIAS-003, REQ-BIAS-004, REQ-BIAS-007, REQ-BIAS-008, REQ-BIAS-010]
commit: null
---

## What was done

`specs/015-pit-dataset/spec.md`: five user stories, 17 functional requirements,
10 success criteria, two ADRs.

## What was decided

- **Six of PRD §41's eleven rules are closed here; five are not**
  ([[ADR-024]]). The five each have a stated reason: rule 2 is enforced for the
  extrema engine and nowhere else, and a constraint enforced in one place is
  not satisfied; 5 needs REQ-WP-013, 6 needs REQ-WP-014/015, 9 has no economic
  metric to include costs in ([[ADR-009]]), and 11 is experiment tracking.
- **Rule 4 is honoured more strictly than written.** The PRD says "no using
  final daily high/low before daily close"; the join refuses a feature derived
  from *any* bar unfinalized at the as-of time. A 15-minute bar read before it
  closed is the same defect at a different scale.
- **Labels are legal because of `known_at`.** Rule 3 permits a future-requiring
  pivot when "the feature availability time is shifted to confirmation time",
  and REQ-WP-019's confirmed extrema already carry exactly that. The rule's
  escape clause and §13A.1's design are the same idea.
- **An empty dataset fails its leakage check** ([[ADR-025]]). Every check here
  is "no row violates X", which passes trivially over nothing — and a build
  that silently produced nothing followed by a clean report reads exactly like
  success. Three earlier features in this repository shipped a guard for this
  shape after the fact.

## What is still open

- **PRD §23.5B's regression targets** — bars to next extremum, next extreme
  return, quantiles — are not built. §23.5A's classification is.
- **No storage**: §24.1's feature snapshot table is unbuilt, so the dataset is
  built from values in memory. The row shape matches the table's columns, so
  persistence later is a change of source rather than of meaning.
- **No model.** Principle IV forbids one until baselines pass leakage tests,
  and this feature is what makes those tests possible.
