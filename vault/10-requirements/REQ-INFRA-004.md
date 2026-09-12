---
id: REQ-INFRA-004
title: The mutation sweep is a committed tool, not a script somebody retyped
type: infrastructure
prd_ref: "§0.9, §0.14"
prd_lines: "28, 33"
phase: null
status: implemented
depends_on: [REQ-INFRA-002]
tags: [tooling, testing]
---

## Requirement

PRD §0.9 requires that code be testable, and §0.14 puts correctness ahead of
performance. Neither mentions mutation testing — **this is a practice of this
repository, not of the PRD**, and that is precisely why it needs recording.

**Thirty-six outcome notes and five ADRs cite a mutation sweep.** [[ADR-047]]
credits one with finding a quantile band that was never enforced. Phrases like
"23 of 23 caught" are the evidence on which requirements were moved to
`implemented`.

**None of it is reproducible.** The sweeps ran from throwaway scripts, retyped
per requirement and never committed. So:

- a flaw in one is a flaw in all of them, and a fix in one fixes nothing else;
- nobody but the author can re-run a sweep or check a claimed number;
- the survivors' reasons — the genuinely valuable part — live only as prose in
  an outcome note, where nothing tests whether they are still true.

**The flaw is not hypothetical.** Python validates its bytecode cache on
`(mtime, size)`. Two consecutive mutants producing files of identical size
within one second reuse the first's `.pyc`, so the second run executes the
first's code and reports its result. Found on 2026-09-12, in the direction that
costs work rather than hides it; the other direction turns a survivor into a
reported catch, and nothing would have shown it.

**A worse flaw was never hit and was always possible.** None of the scripts
checked that the suite was green before mutating. Against a red suite every
mutant is "caught", and the sweep reports a perfect score for a test file that
does not run.

## Acceptance

- The sweep runs from a committed tool over committed mutation specifications,
  and the same command reproduces any number claimed in an outcome note.
- The tool refuses to start unless the unmutated suite passes, so a red baseline
  cannot be reported as a perfect score.
- A mutation whose pattern no longer matches the source is an error, not a
  skip — a pattern that stopped matching means the code moved, which is exactly
  when the sweep must say so.
- A pattern matching more than once is an error, so no mutation silently applies
  to the first of several sites.
- Bytecode caching is disabled for every run, and a test proves that two
  same-size mutants in succession are each evaluated on their own code.
- The source file is restored whatever happens, including a timeout, and a test
  proves it.
- A mutant that hangs counts as caught, because a suite would never let it
  through.
- A survivor must carry a recorded reason, and a survivor that starts being
  caught fails the sweep — so the reason cannot quietly go stale.
- A mutant with no recorded reason that survives fails the sweep.

## Notes

Human territory. Never machine-rewritten.

**The `survives` field is the point of the exercise.** Every sweep in this
repository has ended with a handful of survivors and a paragraph explaining why
each is acceptable — an unreachable branch, a guard a later guard covers, a
contract's own comment that could not be reproduced. Those paragraphs are the
accumulated understanding, and until now nothing checked them. Making a
now-caught survivor a failure turns each one into an assertion with a date on it.

**This is an acceptance audit, not a regression gate.** It answers "are these
tests worth having", which is a question asked when the tests are written.
Whether it belongs in CI is a question of what it costs to run, and that is
measured rather than assumed.
