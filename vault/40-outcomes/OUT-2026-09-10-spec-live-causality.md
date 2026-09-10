---
id: OUT-2026-09-10-spec-live-causality
step: spec
records: [REQ-BIAS-002]
commit: null
---

## What was done

`specs/058-live-causality/spec.md`: three user stories, 9 functional
requirements, 7 success criteria. [[REQ-BIAS-002]] leaves `draft` — it had no
linked artifact of any kind.

## What was decided

- **The gap is named with evidence, not asserted.** Each claim was checked before
  it was written: `require_causal` has one call site outside its own module and
  it is in a research comparison; the forbidden-import scan globs
  `src/channelflow/extrema/` and there are 27 other packages; every occurrence of
  `point_in_time_safe` in `src/` is `True` and no rule reads the field.
- **Every package is scanned unless explicitly exempt.** The inversion
  [[REQ-BIAS-011]] used a day earlier, for the same reason: a package added later
  should join the rule rather than escape it, and a hand-maintained list of what
  to check is a thing someone forgets.
- **The exemption carries a reason and fails when it goes stale.** This is where
  a rule like this erodes. An entry naming a deleted package is how a list stops
  describing anything while still reading as authority.
- **A declaration is not turned into a detection.** [[ADR-022]] settled that a
  general detector is not achievable, and `causality.py` already records that a
  transform lying about itself is Test A's business. This widens the reach of two
  guards; it does not change what they can see.
- **An import edge is not a call.** A live package importing a research module is
  out of scope, named rather than left ambiguous — otherwise the first legitimate
  shared helper would force either a false failure or a silent exemption.

## What is still open

- **`require_causal` still has no live call site, and this spec does not add
  one.** The two checks here are static: what a package imports, and what the
  registry declares. The guard that refuses a centred transform at the moment it
  enters live computation is only reachable from a path that does not exist yet
  — nothing in the repository computes live features from declared transforms.
  That is the third gap, and it is a bigger one than either of these.
- **How many packages the exemption list will need is unknown.** `research/` is
  the obvious one; whether `models/`, `turning/` or `extrema/` legitimately need
  centred helpers is plan work, and each entry that turns out to be needed is a
  finding rather than a formality.
