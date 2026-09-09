---
id: SPEC-056-replay-recorder
requirement: REQ-PIPE-001
speckit_path: specs/056-replay-recorder/spec.md
status: draft
---

## Summary

Three requirements built the canonical plane and its seven tables and each
recorded the same open question in its own words: nothing writes to them. This
is that half.

PRD §25.1 has two backtest modes. This is the replay one, wired to §29.B's
tables through the hooks the producing subsystems already offer —
`BarBuilder.on_final`, and two observers the runner gained. A live feed
therefore has no second path to take, which is the point: a recorded stream
fills the tables by the same route a live one would.

The one design decision worth reading twice concerns signals. The machine
returns the live candidate on every bar it is alive for, each time a more
complete version of the same frozen object, and the obvious recorder writes what
it is given — a row per bar, each a partial history of one signal. Nothing about
those rows is malformed; a reader counting signals would simply count bars. The
recorder keeps the latest per `opened_at_ns` and writes at the end.

The result carries the dataset identity of what it wrote, which is the first of
PRD §0 item 13's four hashes and the thing [[REQ-REPRO-001]] had nothing to
point at.

## Links

- Requirement: [[REQ-PIPE-001]]
- Closes the open question in: [[REQ-STORE-001]], [[REQ-TBL-001]], [[REQ-STORE-002]]
- Builds on: [[REQ-WP-010]], [[REQ-WP-005]], [[REQ-REPRO-001]]
