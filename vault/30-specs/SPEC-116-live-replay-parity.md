---
id: SPEC-116-live-replay-parity
requirement: REQ-NRT-PARITY
speckit_path: specs/116-live-replay-parity/spec.md
status: draft
---

## Summary

§35.5 asks for a live segment replayed offline with feature, channel and signal
parity. Capturing the segment found that the raw archive was replacing each
minute with its own tail — 45 of 45 minutes short, one of them by 465 frames of
744. The spec stands; the parity assertion waits on a segment captured after
the fix.

## Links

- Requirement: [[REQ-NRT-PARITY]]
