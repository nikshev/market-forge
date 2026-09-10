---
id: SPEC-057-experiment-gate-adoption
requirement: REQ-BIAS-011
speckit_path: specs/057-experiment-gate-adoption/spec.md
status: draft
---

## Summary

[[REQ-REPRO-001]] built the registry and the gate. [[ADR-054]] then wrote down
what that had and had not achieved: "Rule 11 is enforceable and not yet
enforced. The mechanism exists; none of the seventeen research modules reports
through it." This is the other half.

The framing that shapes the whole spec is ADR-054's own: a registry that is
merely available is an honour system with a database attached. So adoption is
not eighteen modules gaining a call to `record`. It is **the field becoming
something a comparison can be asked for** — a variant name to the configuration
that distinguishes it, plus the variant chosen, if any — so that a comparison
which cannot answer is a failing test rather than a module someone forgot.

Three decisions worth reading twice.

**A comparison that names no winner is not made to name one.** Several
experiments deliberately report a whole field and no choice; `extremum_detectors`
says so in its own docstring. Forcing a winner would manufacture exactly the
claim rule 11 exists to make checkable. Recording is universal; the gate applies
to a result that chose.

**A variant's config is what actually distinguishes it**, not its name. Where a
comparison currently keeps a variant's name and discards its parameters, it
starts keeping them. A config hash that cannot tell two different configurations
apart is a broken hash, not a cheaper one — and it would put N indistinguishable
rows in the registry while looking like full coverage.

**The suite discovers the modules rather than listing them.** Eighteen modules
adopting today is a snapshot; the next module is what decides whether rule 11 is
enforced or was enforced once.

## Links

- Requirement: [[REQ-BIAS-011]]
- Uses, unchanged: [[REQ-REPRO-001]]
- Rule and its reasoning: [[ADR-054]], [[ADR-024]]
- Append-only writes: [[ADR-056]]
