---
id: SPEC-035-lookback-sensitivity
requirement: REQ-EXP-002
speckit_path: specs/035-lookback-sensitivity/spec.md
status: draft
---

## Summary

EXP-002's six lookbacks, and the one-line rule that is the actual experiment:
"do not select solely on maximum PnL; evaluate stability plateau".

That rule cannot be kept by stating it. A report naming the best expectancy and
nothing else *is* selection by maximum PnL whatever surrounds it — so the
recommendation comes from the plateau, the peak is reported beside it in its own
field, and when there is no plateau there is no recommendation. The peak is
never a fallback.

A peak is where the noise happened to help. A plateau is where the choice does
not matter much, which is the only kind of choice that survives new data — and
the recommendation is its centre, because an edge is one noisy neighbour away
from being off it.

## Links

- Requirement: [[REQ-EXP-002]]
- Builds on: [[REQ-EXP-001]], [[REQ-BT-001]]
