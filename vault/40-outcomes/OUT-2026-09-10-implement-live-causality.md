---
id: OUT-2026-09-10-implement-live-causality
step: implement
records: [REQ-BIAS-002]
commit: null
---

## What was done

PRD §41 rule 2 now reaches the live path. `[[ADR-024]]`'s refusal to claim
coverage "on the strength of one engine's guard" is answered by widening two
guards rather than adding a third:

- the forbidden-helper scan reads every module under `src/channelflow/`, with a
  per-module exemption list carrying reasons, which fails when it names a module
  that is not there;
- `FeatureSpec.point_in_time_safe` is `Literal[True]`, so a feature that cannot
  claim point-in-time safety cannot be registered at all.

Eight tests, 1497 in the suite, mypy clean, 8 of 8 mutants caught.

## What was decided

- **No research exemption was added**, though PRD §13A.6 would permit one. None
  is needed: `derivative_turning` writes its own centred labeller rather than
  importing a helper. An exemption for a case that has not arrived is one nobody
  checked, and it would weaken the rule from the day it was written.
- **The exemption is per module.** The only real case is one file, and exempting
  the `extrema` package would have covered every module beside it — in the
  package this rule most wants scanned.
- **A substring match, not an import parse.** [[ADR-022]]'s reasoning: a
  tripwire, not a detector. Parsing imports would gain the ability to ignore a
  docstring and lose `getattr(scipy.signal, "savgol_filter")`.
- **The policy is in source and the walk is in the test.** Which helpers are
  forbidden and which modules are exempt carries the requirement's marker; the
  walk over the tree is a check on the repository, not something the engine
  calls.

## What is still open

- **`require_causal` still has no live call site.** Both checks added here are
  static — what a module imports, and what the registry declares. The guard that
  refuses a centred transform at the moment it enters live computation is
  reachable only from a path that does not exist: nothing computes live features
  from declared transforms. This is the third gap in the rule and the largest of
  the three, and it is unchanged by this work.
- **A registry that fills on import nearly made a check pass vacuously.**
  `REGISTRY` populates as a side effect of importing the modules that register
  into it, so `all(...)` over it was true and empty on the first run. Caught only
  because the test asserted non-emptiness first. Any future check reading
  `REGISTRY` has the same trap waiting and nothing warns about it.
- **The scan cannot see a helper written by hand.** Someone implementing a
  centred moving average inline breaks the rule and imports nothing. That is
  [[ADR-022]]'s stated limit, not a gap this could close, and Test A remains the
  backstop for a transform that lies about itself.
