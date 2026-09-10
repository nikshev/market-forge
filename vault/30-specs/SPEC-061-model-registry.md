---
id: SPEC-061-model-registry
requirement: REQ-WP-022
speckit_path: specs/061-model-registry/spec.md
status: draft
---

## Summary

PRD §0 item 13 wants four hashes behind every research result.
[[REQ-REPRO-001]] built all four components, and three have producers. The
fourth does not — `ModelArtifact` appears nowhere outside
`channelflow.experiments`, so every run that fitted a model records
`UNRECORDED`, the value whose entire job is to say the run cannot be repeated.

Models are constructed by a caller, fitted in place, and dropped. Two runs of one
experiment over one dataset leave two models nothing can tell apart.

PRD §23.9 names eleven fields, and one of them is the artifact hash — which
settles what the hash is *of*: the model, not the registration describing it.

Three decisions worth reading twice.

**The hash covers exact bytes.** Two fits differing in the last bit produce
different probabilities, so they are different models. A hash that rounded them
together would lie about the one thing it exists to certify, and a platform
producing different bytes has produced a different artifact.

**The model says whether it is fitted.** Only it knows, and the answer cannot be
inferred from outside — `ElasticNetLogistic` holds `_weights = None` and a GMDH
network holds empty layers. The protocol gains one member, the way
`Transform.centered` did, so an author cannot skip the question.

**A hash nobody can resolve is refused.** A run citing an unregistered artifact
is a different kind of unreproducible from a run citing none, and the gate
should accept neither.

## Links

- Requirement: [[REQ-WP-022]]
- The three hashes that already have producers: [[REQ-REPRO-001]], [[REQ-PIPE-001]]
- The gate that has been refusing on this component: [[ADR-054]]
- The models it registers: [[REQ-WP-018]]
