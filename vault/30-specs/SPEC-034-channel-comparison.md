---
id: SPEC-034-channel-comparison
requirement: REQ-EXP-001
speckit_path: specs/034-channel-comparison/spec.md
status: draft
---

## Summary

EXP-001's five channel models over one series, reporting its seven metrics.

Two things had to exist first. [[REQ-CHAN-001]] built baselines B, C and D, and
[[REQ-BT-001]] built the outcomes, fills and costs the seventh metric needs —
which is why this experiment sat at `draft` while its requirement note was
written on the same day as the others.

[[ADR-049]] records the two metric definitions that had a real choice behind
them: a false perfect touch is a bar the *current* channel calls a touch and the
channel of the time did not — the repaint a chart shows — and computational cost
is a deterministic operation count rather than a stopwatch reading, because a
report that cannot be compared with itself cannot be compared with another.

## Links

- Requirement: [[REQ-EXP-001]]
- Decision: [[ADR-049]]
- Builds on: [[REQ-CHAN-001]], [[REQ-BT-001]], [[REQ-WP-010]]
