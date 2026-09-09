---
id: SPEC-028-repaint-comparison
requirement: REQ-US-003
speckit_path: specs/028-repaint-comparison/spec.md
status: draft
---

## Summary

PRD §27.5's two views in one answer, with the difference measured rather than
left to the reader.

The existing toggle compares two views of one information set: `channels.py`
caps its refit at the requested instant. [[REQ-US-003]] asks for "the model's
**later** state", which needs the refit to see later bars — and that is what
makes a repaint visible at all.

[[ADR-046]] is the record. Constitution Principle I governs what a feature may
see; here the hindsight is the subject of the measurement. Three things keep it
from leaking: the span is stated in nanoseconds on every answer, the payload
declares itself research-only, and a test asserts no signal-path module imports
this one — checked over import lines, because "comparison" is ordinary English
and appears in those packages' prose.

## Links

- Requirement: [[REQ-US-003]]
- Decision: [[ADR-046]], reusing [[ADR-040]]'s device
- Builds on: [[REQ-API-001]], [[REQ-WP-006]]
