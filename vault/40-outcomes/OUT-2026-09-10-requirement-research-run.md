---
id: OUT-2026-09-10-requirement-research-run
step: requirement
records: [REQ-WP-024]
commit: null
---

## What was done

[[REQ-WP-024]] extracted from the open questions of five requirements rather
than from a PRD section, because the gap is between them rather than in any one.

## What was decided

- **The caller is the requirement.** Five notes recorded the same gap in their
  own words and each answered it with "a caller will do it". Writing that caller
  down as a requirement is what stops the sixth mechanism being built instead.
- **Assembled refusals are the point.** Each mechanism refuses something — a
  dirty tree, an unregistered artifact, a variant missing from the field, a thin
  horizon. Separately each refusal is theoretical; together they decide whether a
  result is reproducible in the sense PRD §0 item 13 means.
- **One artifact per variant, not per fold.** A variant is fitted once per fold,
  so several fitted models sit behind one comparison. What a result cites is the
  variant *as run*, so the hash covers the folds together. Registering each fold
  separately would produce artifacts nothing cites and leave the run's identity
  ambiguous.
- **One experiment is wired, on purpose.** [[REQ-EXP-008]]'s baseline comparison
  is what PRD §45's Phase 7 acceptance turns on. A second experiment is a second
  caller of the same path — and if it turns out to need a different path, that is
  a finding about the path rather than a reason to wire two now.

## What is still open

- **`compare()` does not return what it fitted.** The models are local to it, so
  either it starts reporting their artifacts or the run refits them on its own.
  Refitting would be a second scoring path, which this repository has repeatedly
  refused; reporting is a change to a type several callers read. Which one is
  right is plan work and is the main risk to the shape above.
- **`require_causal` is not part of this.** It belongs at the entrance to a live
  feature path, and a research run is not one. That gap stays where
  [[REQ-BIAS-002]] left it.
