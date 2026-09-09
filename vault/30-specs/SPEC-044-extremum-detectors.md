---
id: SPEC-044-extremum-detectors
requirement: REQ-EXP-011
speckit_path: specs/044-extremum-detectors/spec.md
status: draft
---

## Summary

EXP-011's five swing methods are [[REQ-WP-019]]'s five threshold modes, run
through the production detector — the non-repainting guarantee lives in that
lifecycle, and a comparison that reimplemented it would be comparing its own
copy.

Two things about the fifth mode had to be fixed before it could be compared at
all. `CHANNEL_WIDTH_FRACTION` needs a channel width and `on_bar` had no way to
supply one, so the mode existed in the policy and could never fire. And its
parameter was named `_pct` while being read as a fraction of price: wired to
`ChannelSnapshot.width_pct`, the only producer of that number, the two differ by
a hundred — a real 2% channel became a 5,000 bps threshold and the detector
silently stopped confirming.

Nothing is ranked. The five metrics pull against each other by construction: a
detector that confirms sooner confirms more and confirms noise, and a single
score would hide the choice rather than inform it.

## Links

- Requirement: [[REQ-EXP-011]]
- Builds on: [[REQ-WP-019]], [[REQ-BT-001]], [[REQ-CHAN-001]]
