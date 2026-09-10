---
id: OUT-2026-09-10-plan-live-causality
step: plan
records: [REQ-BIAS-002]
commit: null
---

## What was done

`specs/058-live-causality/`: `plan.md`, `research.md`, `data-model.md`,
`contracts/scan.md`, `quickstart.md`. Constitution Check passes with no
violations.

[[REQ-BIAS-002]] is `hard_gated`, so `/sdd-plan` step 4 forbids `planned`: the
failing test comes first and the status goes straight to `tested`.

**RED, before `EXEMPT` and `forbidden_in` existed:**

    tests/unit/extrema/test_live_causality.py:22: in <module>
        from channelflow.extrema.causality import EXEMPT, FORBIDDEN_IMPORTS, forbidden_in
    E   ImportError: cannot import name 'EXEMPT' from 'channelflow.extrema.causality'
    ERROR tests/unit/extrema/test_live_causality.py
    !!!!!! Interrupted: 1 error during collection !!!!!!

## What the survey changed

Running the scan before planning changed two decisions:

- **Only one file in the repository holds a forbidden helper**, and it is
  `extrema/causality.py`, which names them in order to forbid them. No research
  module imports one — `derivative_turning` writes its own centred labeller. So
  **no research exemption was added**: PRD §13A.6 would permit one, and an
  exemption for a case that has not arrived is one nobody checked.
- **The exemption became per module rather than per package.** The only real
  case is one file, and exempting `extrema` would have exempted every module
  beside it — in the package this rule most wants to look at. The spec's FR-002,
  FR-003, SC-003 and SC-004 were amended to match.

## What was decided

- **`point_in_time_safe` narrows to `Literal[True]`.** A required field nothing
  reads is documentation. The type makes an unsafe feature unregisterable rather
  than registerable-and-caught-later, and the author still writes the value out,
  so [[ADR-015]]'s "no field an author can forget to think about" is unchanged.
- **Substring match, not an import parse.** [[ADR-022]]'s reasoning: this is a
  tripwire, not a detector. Parsing imports would ignore a docstring and would
  also miss `getattr(scipy.signal, "savgol_filter")` — a real hole traded for a
  cosmetic one.
- **The policy lives in source, the walk lives in the test.** Which helpers are
  forbidden and which modules are exempt is policy and carries the requirement's
  marker; walking the tree is a check on the repository, not a function the
  engine calls.

## What the mutation sweep found

8 mutants over the guard and the registry; 8 caught, one of them only after the
test was fixed.

- **N5 (the forbidden list is emptied) survived the first pass**, and the gap was
  real. The test looped over `FORBIDDEN_IMPORTS`, so deleting an entry shrank the
  loop and the test still passed — which is exactly how a list like this empties
  without anyone noticing. The five are now named explicitly, and asserted as
  membership rather than equality: adding a helper is how the rule grows, and
  removing one should need an argument.

## A false alarm worth recording

`make validate` went red on a test that passed a minute earlier, and the failure
was impossible to read from the code: `forbidden_in("argrelextrema")` returned
the right answer while `forbidden_in("import argrelextrema")` returned nothing,
against a body that is a plain substring match. Executing the file's source
directly gave the correct answer; importing the module did not.

The cause was my own mutation sweep. Mutant N8 replaced `helper in source` with
`helper == source` — **the same number of bytes** — and the restore landed within
the same second. CPython validates a `.pyc` against the source's mtime and size,
so neither changed and the cached bytecode from the mutant was reused. The
symptom was a function that behaved like an equality test while reading like a
substring test.

Worth writing down because the sweep is the tool used to judge whether tests are
worth anything, and a same-length mutation can leave it poisoning later runs.
`find src -name __pycache__ -delete` before trusting a post-sweep result, or
prefer mutations that change the byte count.

## What is still open

- **A registry that fills on import nearly made a check pass vacuously.**
  `REGISTRY` is populated as a side effect of importing the modules that register
  into it, so `all(spec.point_in_time_safe for spec in REGISTRY.values())` was
  true over an empty dict on the first run. Caught only because the test asserted
  the registry was non-empty first. Any future check reading `REGISTRY` has the
  same trap waiting, and nothing warns about it.
- **`require_causal` still has no live call site**, unchanged from the spec's
  open questions. The two checks here are static — what a module imports, and
  what the registry declares. Nothing computes live features from declared
  transforms yet, so the guard that would refuse one at that moment has nowhere
  to sit.
