---
id: OUT-2026-09-14-implement-phase-accounting
step: implement
records: [REQ-WP-069]
commit: null
---

## What was done

`not_delivered:` became three lists, with a cost attached to two of them. 19
tests.

## The measure had stopped measuring

Phase 4 held three entries: Uniswap v4 quoting that nobody had built, Curve
twocrypto quoting waiting on Curve to publish source, and Pinot deferred by
[[ADR-002]]. All three in one list meant the phase **could not reach
`implemented` however much of it was finished**, and every answer to "what is
left" counted two things nobody here could do.

I have given that answer several times, each time noting the problem and then
using the number anyway.

## Splitting a list is trivial; the cost is the point

A three-way split is a way to declare victory unless the new lists are expensive
to use. So:

- a `blocked:` entry names **what it waits on**, or it is "not started" renamed;
- a `deferred:` entry names an **ADR that exists** — checked by opening the file,
  because `[[ADR-999]]` satisfies a pattern and defers to nothing.

Without those, moving an entry one list to the right would close any phase at
will, and the split would have made the accounting worse rather than better.

## The guards are tested against bad input

The original checks ran only over the real phase notes, which all pass. A guard
exercised only by inputs that satisfy it is a guard nobody has seen work, so
`check_blocked` and `check_deferred` are functions now, and four tests hand them
entries that should be refused.

## R8 refused the shortcut

The requirement's whole deliverable was a convention and its guard, so nothing in
`src/` carried its trace and R8 failed: "status 'implemented' requires at least
one source file". Adding `# @trace:` to the test would have satisfied the rule
and meant nothing.

The honest answer was that the guards are tooling, not test code. They live in
`tools/trace/phases.py` now and the test exercises them, which is better
structure than what I first wrote and is what the rule was pointing at.

## What it changed

Phase 4 still cannot close — it has one real entry left, `CUSTOM_ACCOUNTING`
quoting. That is the right answer and it is now the *only* thing standing there.
Nothing else moved: ten phases were already `implemented` with all three lists
empty.
