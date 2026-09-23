---
id: SPEC-119-chart-timeframe-control
requirement: REQ-WP-074
speckit_path: specs/119-chart-timeframe-control/spec.md
status: draft
---

## Summary

The chart parses the link's `tf` and then asks for fifteen minutes regardless,
so a correct series is fetched at the wrong timeframe and renders as empty. The
spec settles the three things [[REQ-WP-074]] says are one mechanism: the
timeframe control re-reads bars, channel, features and extrema at the chosen
duration; the link stays the **initial** value — the entry every alert carries —
while a change writes the address back so a copy reproduces the screen; and the
offered set comes from a new read reporting what this deployment produces
rather than a list written into the frontend, which would be the second source
[[REQ-WP-073]]'s FR-002 forbids. An unhonourable token — unparseable, a calendar
period, or simply not produced here — is refused visibly rather than silently
substituted, because a silent fallback shows one timeframe's candles under
another's name.

## Links

- Requirement: [[REQ-WP-074]]
- Depends on: [[REQ-WP-073]], [[REQ-WP-009]]
