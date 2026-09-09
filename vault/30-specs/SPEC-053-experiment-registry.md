---
id: SPEC-053-experiment-registry
requirement: REQ-REPRO-001
speckit_path: specs/053-experiment-registry/spec.md
status: draft
---

## Summary

PRD §0 item 13 asks for every research result to be reproducible from a
versioned dataset, a config, a code commit hash and a model artifact hash.
[[ADR-053]] built the first. This is the other three, plus the registry that
holds them and the gate that makes both of them mean something.

The interesting part is what happens when a component is not available. Three
failure modes look identical in a record of four strings: a run that fits no
model, a run whose artifact nobody wrote down, and a commit taken from a dirty
working tree. The first is reproducible; the other two are not, and the third is
the one that looks most convincing — the hash resolves, the commit exists, and
the code that ran is gone.

PRD §41 rule 11 — store all discarded experiment variants — meets §0 item 13 at
the same place, because neither is enforceable as storage. Nobody can verify
what was considered and never written down. What can be verified is a claim
about a field: reporting a winner means naming the variants it beat, and every
one of them has to already be in the registry. [[ADR-054]] records that, and the
module states the limit plainly — this cannot stop someone who never mentions a
variant; it stops the one that was run, lost and quietly dropped.

## Links

- Requirements: [[REQ-REPRO-001]], [[REQ-BIAS-011]]
- Decisions: [[ADR-054]], amending [[ADR-024]]
- Builds on: [[REQ-STORE-001]], [[ADR-053]]
